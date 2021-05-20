import os
import sys
import json
import uuid
import logging
import traceback

import dateutil.parser

import zipfile
import tarfile

from pathlib import Path


import csv
import json

from urllib.parse import urlparse
import imageio

from frontend.utils import image_normalize, download_file, check_extension

from django.views import View
from django.http import HttpResponse, JsonResponse
from django.conf import settings


class CollectionUpload(View):
    field_mapping = {
        "title": "meta.title",
        "artist": "meta.artist",
        "object_type": "meta.object_type",
        "year_min": "meta.year_min",
        "year_max": "meta.year_max",
        "date": "meta.year_max",
        "location": "meta.location",
        "medium": "meta.medium",
        "link": "origin.link",
        "origin": "origin.name",
        "meta.title": "meta.title",
        "meta.artist": "meta.artist",
        "meta.object_type": "meta.object_type",
        "meta.year_min": "meta.year_min",
        "meta.year_max": "meta.year_max",
        "meta.location": "meta.location",
        "meta.medium": "meta.medium",
        "origin.link": "origin.link",
        "origin.name": "origin.name",
        "file": "file",
        "path": "file",
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
        for i, x in enumerate(header):
            if x.lower() in self.field_mapping:
                mapped_fields[i] = self.field_mapping[x]
            else:
                unknown_fields.append(x)

        return mapped_fields, unknown_fields

    def parse_csv(self, csv_path):
        entries = []

        with open(csv_path, "r") as f:
            spamreader = csv.reader(f, delimiter=",")
            header = None
            for row in spamreader:
                if header is None:
                    header, unknown_fields = self.parse_header(row)

                    if len(unknown_fields) > 0:
                        return {
                            "status": "error",
                            "error": {"unknown_fields": unknown_fields, "type": "unknown_fields"},
                        }
                    continue
                entry = {}
                for i, element in enumerate(row):
                    if not element:
                        continue
                    if i in header:
                        key = header[i]
                        # parse of special fields
                        if key in ["meta.year_min", "meta.year_max"]:
                            element = self.parse_date_to_year(element)
                            if element is None:
                                continue

                        if key in entry:
                            if not isinstance(entry[key], (list, set)):
                                entry[key] = [entry[key]]
                            entry[key].append(element)
                        else:
                            entry[key] = element

                entries.append(entry)

        return {"status": "ok", "data": {"entries": entries}}

    def parse_meta(self, meta_path):
        if check_extension(meta_path, extensions=[".csv"]):
            return self.parse_csv(meta_path)

    def parse_zip(self, image_path):
        result_paths = []
        try:
            file = zipfile.ZipFile(image_path, "r")
            for name in file.namelist():
                if check_extension(name, extensions=[".jpg", ".gif", ".png", ".jpeg"]):
                    result_paths.append({"path": name, "filename": Path(name).stem})
        except Exception as e:
            print(e, flush=True)
            return {
                "status": "error",
                "error": {"type": "corrupt_archives_file"},
            }

        return {"status": "ok", "data": {"entries": result_paths}}

    def parse_image(self, image_path):
        if check_extension(image_path, extensions=[".zip"]):
            return self.parse_zip(image_path)

    def merge_meta_image(self, meta_entries, image_entries):
        def path_sim(a, b):
            merged_paths = list(zip(image_path.parts[::-1], meta_path.parts[::-1]))
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
            entries.append({**meta, **image})

        return {"status": "ok", "data": {"entries": entries}}

    def post(self, request):
        try:
            if request.method != "POST":
                return JsonResponse({"status": "error"})

            collection_id = uuid.uuid4().hex

            output_dir = os.path.join(settings.UPLOAD_ROOT, collection_id[0:2], collection_id[2:4])

            print(collection_id, flush=True)
            print(request.FILES, flush=True)

            meta_parse_result = None

            # Check meta file first
            if "meta" in request.FILES:
                meta_result = download_file(
                    output_dir=output_dir,
                    output_name=collection_id,
                    file=request.FILES["meta"],
                    max_size=2 * 1024 * 1024,
                    extensions=(".csv", ".json", ".jsonl"),
                )
                if meta_result["status"] != "ok":
                    return JsonResponse(meta_result)

                meta_parse_result = self.parse_meta(meta_result["path"])
                print(meta_parse_result, flush=True)
                if meta_parse_result["status"] != "ok":
                    return JsonResponse(meta_parse_result)

            # Check image file
            if "image" not in request.FILES:
                return JsonResponse(
                    {
                        "status": "error",
                        "error": {"type": "no_images"},
                    }
                )

            image_result = download_file(
                output_dir=output_dir,
                output_name=collection_id,
                file=request.FILES["image"],
                max_size=200 * 1024 * 1024,
                extensions=(".zip", ".tar", ".tar.gz", ".tar.bz2", ".tar.xz"),
            )
            if image_result["status"] != "ok":
                return JsonResponse(image_result)

            image_parse_result = self.parse_image(image_result["path"])
            if image_parse_result["status"] != "ok":
                return JsonResponse(image_parse_result)

            # Check if meta and image match
            if meta_parse_result is not None:
                image_parse_result = self.merge_meta_image(
                    meta_parse_result["data"]["entries"], image_parse_result["data"]["entries"]
                )
                if image_parse_result["status"] != "ok":
                    return JsonResponse(image_parse_result)

            return JsonResponse({"status": "error"})

        except Exception as e:
            logging.error(traceback.format_exc())
            return JsonResponse({"status": "error"})
