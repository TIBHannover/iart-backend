import logging
import sys
import os
import json
import uuid
from urllib.parse import urlparse

import imageio
import numpy as np
import traceback

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, Http404
from django.conf import settings
from django.contrib import auth
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt


# from iart_indexer.database.elasticsearch_database import ElasticSearchDatabase
# from iart_indexer.database.elasticsearch_suggester import ElasticSearchSuggester

import json

from rest_framework import viewsets

if settings.INDEXER_PATH is not None:
    sys.path.append(settings.INDEXER_PATH)
    print(sys.path)

import grpc
from iart_indexer import indexer_pb2, indexer_pb2_grpc
from iart_indexer.utils import meta_from_proto, classifier_from_proto, feature_from_proto, suggestions_from_proto

from .utils import image_normalize


def upload(request):
    print("#####################", flush=True)
    print(request.FILES, flush=True)
    try:
        if request.method != "POST":
            return JsonResponse({"status": "error"})

        image = None
        image_id = uuid.uuid4().hex
        title = ""
        if "file" in request.FILES:
            data = request.FILES["file"].read()
            if data is not None:
                image = image_normalize(imageio.imread(data))
                title = request.FILES["file"].name

        if "url" in request.POST:
            url_parsed = urlparse(request.POST["url"])
            if url_parsed.netloc:
                image = image_normalize(imageio.imread(request.POST["url"]))
                title = os.path.basename(url_parsed.path)

        if image is not None:
            output_dir = os.path.join(settings.UPLOAD_ROOT, image_id[0:2], image_id[2:4])
            os.makedirs(output_dir, exist_ok=True)
            imageio.imwrite(os.path.join(output_dir, image_id + ".jpg"), image)

            return JsonResponse(
                {
                    "status": "ok",
                    "entries": [{"id": image_id, "meta": {"title": title}, "path": upload_url_to_image(image_id)}],
                }
            )

        return JsonResponse({"status": "error"})

    except Exception as e:
        print(e)
        logging.error(traceback.format_exc())
        return JsonResponse({"status": "error"})
