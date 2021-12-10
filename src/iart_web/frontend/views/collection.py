import os
import csv
import sys
import json
import uuid
import imageio
import logging
import zipfile
import tarfile
import traceback
import dateutil.parser

from pathlib import Path
from urllib.parse import urlparse

from django.views import View
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.db.models import Count
from django.core.exceptions import BadRequest

from frontend.tasks import collection_upload
from frontend.models import Collection, Image
from frontend.utils import image_normalize, download_file, check_extension, unflat_dict

logger = logging.getLogger(__name__)


class CollectionUpload(View):
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

    def parse_date_to_year(self, date):
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
                    value = self.parse_date_to_year(value)

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
                return {"status": "error", "error": {"type": "no_valid_colnames"}}

            for row in reader:
                entries.append(self.parse_entry(row, mapped_fields))

        return {"status": "ok", "data": {"entries": entries}}

    def parse_json(self, json_path):
        entries = []

        with open(json_path, "r", encoding="utf-8") as f:
            for row in json.load(f):
                mapped_fields, _ = self.parse_header(row.keys())

                if len(mapped_fields) > 0:
                    entries.append(self.parse_entry(row, mapped_fields))

        if len(entries) == 0:
            return {"status": "error", "error": {"type": "no_valid_colnames"}}

        return {"status": "ok", "data": {"entries": entries}}

    def parse_jsonl(self, jsonl_path):
        entries = []

        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                mapped_fields, _ = self.parse_header(row.keys())

                if len(mapped_fields) > 0:
                    entries.append(self.parse_entry(row, mapped_fields))

        if len(entries) == 0:
            return {"status": "error", "error": {"type": "no_valid_colnames"}}

        return {"status": "ok", "data": {"entries": entries}}

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
            return {"status": "error", "error": {"type": "corrupt_archives_file"}}

        return {"status": "ok", "data": {"entries": entries}}

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
                return {"status": "error", "error": {"type": "image_has_no_entry"}}

            entries.append({**best_meta, **image})

        return {"status": "ok", "data": {"entries": entries}}

    def post(self, request):
        if not request.user.is_authenticated:
            raise BadRequest("not_authenticated")

        try:
            if request.method != "POST":
                raise BadRequest()

            collection_id = uuid.uuid4().hex
            visibility = "user"

            output_dir = os.path.join(
                settings.UPLOAD_ROOT,
                collection_id[0:2],
                collection_id[2:4],
            )

            collection_name = request.POST.get("name")

            if collection_name is None:
                raise BadRequest("collection_name_not_defined")
            if len(collection_name) < 5:
                raise BadRequest("collection_name_to_short")
            if len(collection_name) > 25:
                raise BadRequest("collection_name_to_long")

            meta_parse_result = None

            if "meta" in request.FILES:
                meta_result = download_file(
                    output_dir=output_dir,
                    output_name=collection_id,
                    file=request.FILES["meta"],
                    max_size=2 * 1024 * 1024,
                    extensions=(".csv", ".json", ".jsonl"),
                )

                if meta_result["status"] != "ok":
                    raise BadRequest(meta_result["error"]["type"])

                meta_parse_result = self.parse_meta(meta_result["path"])

                if meta_parse_result["status"] != "ok":
                    raise BadRequest(meta_parse_result["error"]["type"])

            if "image" not in request.FILES:
                raise BadRequest("no_images")

            image_result = download_file(
                output_dir=output_dir,
                output_name=collection_id,
                file=request.FILES["image"],
                max_size=200 * 1024 * 1024,
                extensions=(
                    ".zip", ".tar", ".tar.gz",
                    ".tar.bz2", ".tar.xz",
                ),
            )

            if image_result["status"] != "ok":
                raise BadRequest(image_result["error"]["type"])

            image_parse_result = self.parse_image(image_result["path"])

            if image_parse_result["status"] != "ok":
                raise BadRequest(image_parse_result["error"]["type"])

            # Check if meta and image match
            if meta_parse_result is not None:
                image_parse_result = self.merge_meta_image(
                    meta_parse_result["data"]["entries"], 
                    image_parse_result["data"]["entries"],
                )

                if image_parse_result["status"] != "ok":
                    raise BadRequest(image_parse_result["error"]["type"])

            entries = list(map(unflat_dict, image_parse_result["data"]["entries"]))

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

            return JsonResponse({"status": "ok"})
        except Exception as e:
            logger.error(traceback.format_exc())

            raise BadRequest(e)


class CollectionList(View):
    def get(self, request):
        if not request.user.is_authenticated:
            raise BadRequest("not_authenticated")

        try:
            collections = []

            user_collections = Collection.objects.filter(user=request.user)

            for collection in user_collections.annotate(count=Count("image")):
                collections.append(
                    {
                        "hash_id": collection.hash_id,
                        "name": collection.name,
                        "status": collection.status,
                        "progress": collection.progress,
                        "date": collection.date,
                        "count": collection.count,
                    }
                )

            return JsonResponse({"status": "ok", "collections": collections})
        except Exception as e:
            logging.error(traceback.format_exc())

            raise BadRequest(e)


class CollectionDelete(View):
    def post(self, request):
        if not request.user.is_authenticated:
            raise BadRequest("not_authenticated")

        try:
            body = request.body.decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            body = request.body

        try:
            data = json.loads(body)
        except Exception as e:
            raise BadRequest()

        if "params" not in data:
            raise BadRequest()

        params = data["params"]

        try:
            collection = Collection.objects.get(hash_id=params["hash_id"])
            images = Image.objects.filter(collection=collection)

            for image in images.values("hash_id"):
                for res in settings.IMAGE_RESOLUTIONS:
                    suffix = res.get("suffix", "")
                    hash_id = image["hash_id"]

                    image_output_file = os.path.join(
                        settings.UPLOAD_ROOT,
                        hash_id[0:2], hash_id[2:4],
                        f"{hash_id}{suffix}.jpg",
                    )

                    if os.path.exists(image_output_file):
                        os.remove(image_output_file)

            images.delete()
            collection.delete()

            # TODO: Remove from Faiss, Elasticsearch

            return JsonResponse({"status": "ok"})
        except Exception as e:
            logging.error(traceback.format_exc())

            raise BadRequest(e)
