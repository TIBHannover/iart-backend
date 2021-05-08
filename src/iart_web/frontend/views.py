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


def media_url_to_image(id):
    # todo
    return "http://localhost:8000" + settings.MEDIA_URL + id[0:2] + "/" + id[2:4] + "/" + id + ".jpg"


def media_url_to_preview(id):
    # todo
    return "http://localhost:8000" + settings.MEDIA_URL + id[0:2] + "/" + id[2:4] + "/" + id + "_m.jpg"


def upload_url_to_image(id):
    # todo
    return "http://localhost:8000" + settings.UPLOAD_URL + id[0:2] + "/" + id[2:4] + "/" + id + ".jpg"


def upload_url_to_preview(id):
    # todo
    return "http://localhost:8000" + settings.UPLOAD_URL + id[0:2] + "/" + id[2:4] + "/" + id + "_m.jpg"


def upload_path_to_image(id):
    # todo
    return os.path.join(settings.UPLOAD_ROOT, id[0:2], id[2:4], id + ".jpg")


def parse_search_request(request):
    grpc_request = indexer_pb2.SearchRequest()
    weights = {"clip_embedding_feature": 1}

    if "settings" in request:
        if request["settings"].get("layout") == "umap":
            grpc_request.mapping = "umap"

        if request["settings"].get("weights"):
            weights = request["settings"]["weights"]

    if "filters" in request:
        for k, v in request["filters"].items():
            if not isinstance(v, (list, set)):
                v = [v]
            for t in v:
                term = grpc_request.terms.add()
                term.text.field = k
                term.text.query = t

    if "date_range" in request and request["date_range"]:
        date_range = request["date_range"]
        if not isinstance(date_range, (list, set)):
            date_range = [date_range]
        if len(date_range) > 1:
            term = grpc_request.terms.add()
            term.number.field = "meta.yaer_max"
            term.number.int_query = max(date_range)
            term.number.flag = indexer_pb2.NumberSearchTerm.MUST
            term.number.relation = indexer_pb2.NumberSearchTerm.LESS_EQ

        term = grpc_request.terms.add()
        term.number.field = "meta.year_min"
        term.number.int_query = min(date_range)
        term.number.flag = indexer_pb2.NumberSearchTerm.MUST
        term.number.relation = indexer_pb2.NumberSearchTerm.GREATER_EQ

    if "aggregate" in request:
        for field_name in request["aggregate"]:
            grpc_request.aggregate.fields.extend([field_name])
            grpc_request.aggregate.size = 250

    if "query" in request:
        for q in request["query"]:
            if "type" in q and q["type"] == "txt":

                term = grpc_request.terms.add()
                term.image_text.query = q["value"]
                if "weights" in q:
                    plugins = q["weights"]
                    if not isinstance(plugins, (list, set)):
                        plugins = [plugins]
                    for p in plugins:
                        for k, v in p.items():
                            plugins = term.feature.plugins.add()
                            plugins.name = k.lower()
                            plugins.weight = v
                else:
                    for k, v in weights.items():
                        plugins = term.feature.plugins.add()
                        plugins.name = k.lower()
                        plugins.weight = v

                if "positive" in q and not q["positive"]:
                    term.image_text.flag = indexer_pb2.ImageTextSearchTerm.NEGATIVE
                else:
                    term.image_text.flag = indexer_pb2.ImageTextSearchTerm.POSITIVE

            if "type" in q and q["type"] == "idx":

                term = grpc_request.terms.add()
                term.feature.image.id = q["value"]
                if "weights" in q:
                    plugins = q["weights"]
                    if not isinstance(plugins, (list, set)):
                        plugins = [plugins]
                    for p in plugins:
                        for k, v in p.items():
                            plugins = term.feature.plugins.add()
                            plugins.name = k.lower()
                            plugins.weight = v
                else:
                    for k, v in weights.items():
                        plugins = term.feature.plugins.add()
                        plugins.name = k.lower()
                        plugins.weight = v

                if "positive" in q and not q["positive"]:
                    term.feature.flag = indexer_pb2.ImageTextSearchTerm.NEGATIVE
                else:
                    term.feature.flag = indexer_pb2.ImageTextSearchTerm.POSITIVE

            grpc_request.sorting = "feature"

    # TODO use seed from user
    if "random" in request:
        if isinstance(request["random"], (int, float, str)):
            grpc_request.sorting = "random"

    return grpc_request


def rpc_load(query):

    grpc_request = parse_search_request(query)
    print(grpc_request)

    host = settings.GRPC_HOST  # "localhost"
    port = settings.GRPC_PORT  # 50051
    channel = grpc.insecure_channel(
        "{}:{}".format(host, port),
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
        ],
    )
    stub = indexer_pb2_grpc.IndexerStub(channel)
    response = stub.search(grpc_request)

    return {"status": "ok", "job_id": response.id, "state": "pending"}


def rpc_check_load(job_id):

    host = settings.GRPC_HOST  # "localhost"
    port = settings.GRPC_PORT  # 50051
    channel = grpc.insecure_channel(
        "{}:{}".format(host, port),
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
        ],
    )
    stub = indexer_pb2_grpc.IndexerStub(channel)

    request = indexer_pb2.ListSearchResultRequest(id=job_id)

    try:
        response = stub.list_search_result(request)
        entries = []
        for e in response.entries:
            entry = {"id": e.id}

            entry["meta"] = meta_from_proto(e.meta)
            entry["origin"] = meta_from_proto(e.origin)
            entry["classifier"] = classifier_from_proto(e.classifier)
            entry["feature"] = feature_from_proto(e.feature)
            entry["coordinates"] = list(e.coordinates)

            entry["path"] = media_url_to_preview(e.id)
            entries.append(entry)

        aggregations = []
        print("################# aggregations")
        for e in response.aggregate:
            print(e.field_name)
            aggr = {"field": e.field_name, "entries": []}
            for x in e.entries:
                aggr["entries"].append({"name": x.key, "count": x.int_val})

            aggregations.append(aggr)
        return {"status": "ok", "entries": entries, "aggregations": aggregations, "state": "done"}
    except grpc.RpcError as e:

        # search is still running
        if e.code() == grpc.StatusCode.FAILED_PRECONDITION:
            return {"status": "ok", "job_id": job_id, "state": "pending"}

    return {"status": "error", "state": "done"}


def load(request):
    try:
        body = request.body.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        body = request.body

    try:
        data = json.loads(body)
    except Exception as e:
        print("Search: JSON error: {}".format(e))
        return JsonResponse({"status": "error"})

    print(f"############################################", flush=True)
    print(f"Data: {data}", flush=True)
    if "params" not in data:
        return JsonResponse({"status": "error"})

    # Check for existing search job
    if "job_id" in data["params"]:
        response = rpc_check_load(data["params"]["job_id"])
        return JsonResponse(response)
    # Should a new search request
    response = rpc_load(data["params"])

    return JsonResponse(response)


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
