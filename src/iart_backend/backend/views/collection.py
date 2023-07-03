import os
import csv
import sys
import json
import uuid
import grpc
import imageio
import logging
import zipfile
import tarfile
import traceback
import dateutil.parser

from .utils import RPCView
from pathlib import Path
from urllib.parse import urlparse
from django.conf import settings
from django.db.models import Count
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from backend.tasks import collection_upload
from backend.models import Collection, Image
from backend.utils import (
    image_normalize,
    download_file,
    check_extension,
    unflat_dict,
)

if settings.INDEXER_PATH is not None:
    sys.path.append(settings.INDEXER_PATH)

from iart_indexer import indexer_pb2, indexer_pb2_grpc


logger = logging.getLogger(__name__)


class CollectionAdd(APIView):
    field_mapping = {
        "title": "meta.title",
        "meta.title": "meta.title",
        "artist": "meta.artist_name",
        "artist_name": "meta.artist_name",
        "meta.artist": "meta.artist_name",
        "meta.artist_name": "meta.artist_name",
        "object_type": "meta.object_type",
        "meta.object_type": "meta.object_type",
        "year_min": "meta.year_min",
        "meta.year_min": "meta.year_min",
        "year_max": "meta.year_max",
        "meta.year_max": "meta.year_max",
        "date": "meta.year_max",
        "meta.date": "meta.year_max",
        "location": "meta.location",
        "meta.location": "meta.location",
        "institution": "meta.institution",
        "meta.institution": "meta.institution",
        "medium": "meta.medium",
        "meta.medium": "meta.medium",
        "link": "origin.link",
        "origin.link": "origin.link",
        "origin": "origin.name",
        "origin.name": "origin.name",
        "path": "file",
        "id": "id",
    }

    def date_to_year(self, date):
        try:
            return int(date)
        except:
            try:
                return dateutil.parser.parse(date).year
            except:
                return None

    def parse_header(self, header):
        mapped_fields = {}
        unknown_fields = []

        for x in header:
            if self.field_mapping.get(x.lower()):
                mapped_fields[x] = self.field_mapping[x.lower()]
            else:
                unknown_fields.append(x)

        return mapped_fields, unknown_fields

    def parse_entry(self, row, mapped_fields):
        entry = {}

        for key, value in row.items():
            if mapped_fields.get(key):
                field = mapped_fields[key]

                if field in ["meta.year_min", "meta.year_max"]:
                    value = self.date_to_year(value)

                    if value is None:
                        continue

                if field in entry:
                    if not isinstance(entry[field], (list, set)):
                        entry[field] = [entry[field]]

                    entry[field].append(value)
                else:
                    entry[field] = value

        if not entry.get("file"):
            entry["file"] = f'{entry["id"]}.jpg'

        return entry

    def parse_csv(self, csv_path):
        entries = []

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=",")
            mapped_fields, _ = self.parse_header(reader.fieldnames)

            if len(mapped_fields) == 0:
                return None

            for row in reader:
                entries.append(self.parse_entry(row, mapped_fields))

        return entries

    def parse_json(self, json_path):
        entries = []

        with open(json_path, "r", encoding="utf-8") as f:
            for row in json.load(f):
                mapped_fields, _ = self.parse_header(row.keys())

                if len(mapped_fields) > 0:
                    entries.append(self.parse_entry(row, mapped_fields))

        if len(entries) == 0:
            return None

        return entries

    def parse_jsonl(self, jsonl_path):
        entries = []

        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                mapped_fields, _ = self.parse_header(row.keys())

                if len(mapped_fields) > 0:
                    entries.append(self.parse_entry(row, mapped_fields))

        if len(entries) == 0:
            return None

        return entries

    def parse_meta(self, meta_path):
        if check_extension(meta_path, extensions=[".csv"]):
            return self.parse_csv(meta_path)
        elif check_extension(meta_path, extensions=[".json"]):
            return self.parse_json(meta_path)
        elif check_extension(meta_path, extensions=[".jsonl"]):
            return self.parse_jsonl(meta_path)

    def parse_zip(self, image_path):
        entries = []

        try:
            file = zipfile.ZipFile(image_path, "r")

            for name in file.namelist():
                if check_extension(name, extensions=[".jpg", ".gif", ".png", ".jpeg"]):
                    entries.append({"path": name, "filename": Path(name).stem})
        except Exception as e:
            pass

        if len(entries) == 0:
            return None

        return entries

    def parse_image(self, image_path):
        if check_extension(image_path, extensions=[".zip"]):
            return self.parse_zip(image_path)

    def merge_meta_image(self, meta_entries, image_entries):
        def path_sim(a, b):
            merged_paths = list(
                zip(
                    image_path.parts[::-1],
                    meta_path.parts[::-1],
                )
            )

            for i, x in enumerate(merged_paths):
                if x[0] != x[1]:
                    return i

            return len(merged_paths)

        entries = []

        for image in image_entries:
            image_path = Path(image["path"])

            best_sim = 0
            best_meta = None

            for meta in meta_entries:
                meta_path = Path(meta["file"])
                sim = path_sim(image_path, meta_path)

                if sim == 0:
                    continue

                if sim > best_sim:
                    best_meta = meta

            if best_meta is None:
                continue

            entries.append({**best_meta, **image})

        if len(entries) == 0:
            return None

        return entries

    def post(self, request, format=None):
        if not request.user.is_authenticated:
            raise APIException("not_authenticated")

        try:
            collection_id = uuid.uuid4().hex
            visibility = "user"

            output_dir = os.path.join(
                settings.UPLOAD_ROOT,
                collection_id[0:2],
                collection_id[2:4],
            )

            collection_name = request.data.get("name")

            if collection_name is None:
                raise APIException("collection_name_not_defined")

            if len(collection_name) < 5:
                raise APIException("collection_name_too_short")

            if len(collection_name) > 25:
                raise APIException("collection_name_too_long")

            meta_parse_result = None

            if request.data.get("image") is None:
                raise APIException("no_images")

            if request.data.get("meta", "undefined") != "undefined":
                meta_result = download_file(
                    output_dir=output_dir,
                    output_name=collection_id,
                    file=request.data["meta"],
                    max_size=2 * 1024 * 1024,
                    extensions=(".csv", ".json", ".jsonl"),
                )

                if meta_result["status"] != "ok":
                    raise APIException(meta_result["error"]["type"])

                meta_parse_result = self.parse_meta(meta_result["path"])

                if meta_parse_result is None:
                    raise APIException("no_valid_colnames")

            image_result = download_file(
                output_dir=output_dir,
                output_name=collection_id,
                file=request.data["image"],
                max_size=1000 * 1024 * 1024,
                extensions=(
                    ".zip",
                    ".tar",
                    ".tar.gz",
                    ".tar.bz2",
                    ".tar.xz",
                ),
            )

            if image_result["status"] != "ok":
                raise APIException(image_result["error"]["type"])

            image_parse_result = self.parse_image(image_result["path"])

            if image_parse_result is None:
                raise APIException("corrupt_archives_file")

            # Check if meta and image match
            if meta_parse_result is not None:
                image_parse_result = self.merge_meta_image(
                    meta_parse_result,
                    image_parse_result,
                )

                if image_parse_result is None:
                    raise APIException("no_matching_images")

            entries = list(map(unflat_dict, image_parse_result))

            task = collection_upload.apply_async(
                (
                    {
                        "collection_name": collection_name,
                        "collection_id": collection_id,
                        "visibility": visibility,
                        "user_id": request.user.id,
                        "entries": entries,
                        "image_path": str(image_result["path"]),
                    },
                )
            )

            return Response()
        except Exception as error:
            logger.error(traceback.format_exc())

        raise APIException("unknown_error")


class CollectionList(APIView):
    def get(self, request, format=None):
        if not request.user.is_authenticated:
            raise APIException("not_authenticated")

        try:
            user_collections = Collection.objects.filter(user=request.user).annotate(count=Count("image"))

            collections = [
                {
                    "hash_id": collection.hash_id,
                    "name": collection.name,
                    "status": collection.status,
                    "progress": collection.progress,
                    "date": collection.date,
                    "count": collection.count,
                }
                for collection in user_collections
            ]

            return Response(collections)
        except Exception as error:
            logger.error(traceback.format_exc())

        raise APIException("unknown_error")


class CollectionRemove(RPCView):
    def post(self, request, format=None):
        if not request.user.is_authenticated:
            raise APIException("not_authenticated")

        hash_id = request.data["params"].get("hash_id")

        if hash_id is None:
            raise APIException("unknown_error")

        try:
            collection = Collection.objects.get(hash_id=hash_id)
            images = Image.objects.filter(collection=collection)

            for image in images.values("hash_id"):
                for res in settings.IMAGE_RESOLUTIONS:
                    suffix = res.get("suffix", "")
                    hash_id = image["hash_id"]

                    image_output_file = os.path.join(
                        settings.UPLOAD_ROOT,
                        hash_id[0:2],
                        hash_id[2:4],
                        f"{hash_id}{suffix}.{settings.IMAGE_EXT}",
                    )

                    if os.path.exists(image_output_file):
                        os.remove(image_output_file)

            images.delete()
            collection.delete()

            stub = indexer_pb2_grpc.IndexerStub(self.channel)
            request = indexer_pb2.CollectionDeleteRequest(id=hash_id)
            response = stub.collection_delete(request)

            return Response()
        except Exception as error:
            logger.error(traceback.format_exc())

        raise APIException("unknown_error")
