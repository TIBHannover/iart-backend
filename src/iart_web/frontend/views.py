import logging
import sys
import os
import json
import uuid
from urllib.parse import urlparse

import imageio
import numpy as np

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, Http404
from django.conf import settings
from django.contrib import auth
from django.views.decorators.http import require_http_methods

# from iart_indexer.database.elasticsearch_database import ElasticSearchDatabase
# from iart_indexer.database.elasticsearch_suggester import ElasticSearchSuggester

import json

if settings.INDEXER_PATH is not None:
    sys.path.append(settings.INDEXER_PATH)
    print(sys.path)

import grpc
from iart_indexer import indexer_pb2, indexer_pb2_grpc
from iart_indexer.utils import meta_from_proto, classifier_from_proto, feature_from_proto, suggestions_from_proto

from .utils import image_normalize


def media_url_to_image(id):
    # todo
    return settings.MEDIA_URL + id[0:2] + "/" + id[2:4] + "/" + id + ".jpg"


def media_url_to_preview(id):
    # todo
    return settings.MEDIA_URL + id[0:2] + "/" + id[2:4] + "/" + id + "_m.jpg"


def upload_url_to_image(id):
    # todo
    return settings.UPLOAD_URL + id[0:2] + "/" + id[2:4] + "/" + id + ".jpg"


def upload_url_to_preview(id):
    # todo
    return settings.UPLOAD_URL + id[0:2] + "/" + id[2:4] + "/" + id + "_m.jpg"


def upload_path_to_image(id):
    # todo
    return os.path.join(settings.UPLOAD_ROOT, id[0:2], id[2:4], id + ".jpg")



def autocomplete_view(request):
    # if not request.is_ajax():
    # return Http404()

    try:
        body = request.body.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        body = request.body

    try:
        data = json.loads(body)
    except Exception as e:
        print("Search: JSON error: {}".format(e))
        return JsonResponse({"status": "error"})

    if "query" not in data:
        # TODO error
        return JsonResponse({"status": "error"})

    query = data["query"]

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
    request = indexer_pb2.SuggestRequest(query=query)
    response = stub.suggest(request)
    print(response)
    context = {"status": "ok", "suggestions": suggestions_from_proto(response)}

    return JsonResponse(context)


def list_feature_view(request):

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
    request = indexer_pb2.AggregateRequest(size=10, type="count", part="feature")
    response = stub.aggregate(request)

    return JsonResponse({"status": "ok", "features": [x.key for x in response.field if x.int_val > 0]})


def aggregate_view(request):
    #
    # if not request.is_ajax():
    #     return Http404()
    try:
        body = request.body.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        body = request.body

    try:
        data = json.loads(body)
    except Exception as e:
        print("Search: JSON error: {}".format(e))
        return JsonResponse({"status": "error"})

    if "queries" not in data:
        return JsonResponse({"status": "error"})

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
    request = indexer_pb2.AggregateRequest()

    for q in data["queries"]:
        print(q)

        if "type" in q and q["type"] is not None:
            type_req = q["type"]
            if not isinstance(type_req, str):
                return JsonResponse({"status": "error"})

            term = request.terms.add()
            if type_req.lower() == "meta":
                term = request.terms.add()
                term.meta.query = q["query"]
            if type_req.lower() == "annotations":
                term = request.terms.add()
                term.classifier.query = q["query"]
                request.sorting = "classifier"

        elif "query" in q and q["query"] is not None:
            term = request.terms.add()
            term.meta.query = q["query"]

            term = request.terms.add()
            term.classifier.query = q["query"]

        if "reference" in q and q["reference"] is not None:
            request.sorting = "feature"

            term = request.terms.add()
            # TODO use a database for this case
            if os.path.exists(upload_path_to_image(q["reference"])):
                term.feature.image.encoded = open(upload_path_to_image(q["reference"]), "rb").read()
            else:
                term.feature.image.id = q["reference"]

            if "features" in q:
                plugins = q["features"]
                if not isinstance(q["features"], (list, set)):
                    plugins = [q["features"]]
                for p in plugins:
                    for k, v in p.items():
                        plugins = term.feature.plugins.add()
                        plugins.name = k.lower()
                        plugins.weight = v

    if "sorting" in data and data["sorting"] == "random":
        request.sorting = "random"

    if "mapping" in data and data["mapping"] == "umap":
        request.mapping = "umap"

    response = stub.search(request)

    return JsonResponse({"status": "ok", "job_id": response.id})


def search_view(request):
    #
    # if not request.is_ajax():
    #     return Http404()
    try:
        body = request.body.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        body = request.body

    try:
        data = json.loads(body)
    except Exception as e:
        print("Search: JSON error: {}".format(e))
        return JsonResponse({"status": "error"})

    if "queries" not in data:
        return JsonResponse({"status": "error"})
    host = settings.GRPC_HOST  # "localhost"
    port = settings.GRPC_PORT  # 50051
    print(f"Search: GRPC {host}:{port}")
    channel = grpc.insecure_channel(
        "{}:{}".format(host, port),
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
        ],
    )
    stub = indexer_pb2_grpc.IndexerStub(channel)
    request = indexer_pb2.SearchRequest()

    print("BUILD QUERY")
    for q in data["queries"]:
        print(q)

        if "type" in q and q["type"] is not None:
            type_req = q["type"]
            if not isinstance(type_req, str):
                return JsonResponse({"status": "error"})

            term = request.terms.add()
            if type_req.lower() == "meta":
                term = request.terms.add()
                term.meta.query = q["query"]
            if type_req.lower() == "annotations":
                term = request.terms.add()
                term.classifier.query = q["query"]
                request.sorting = "classifier"

        elif "query" in q and q["query"] is not None:
            term = request.terms.add()
            term.meta.query = q["query"]

            term = request.terms.add()
            term.classifier.query = q["query"]

        if "reference" in q and q["reference"] is not None:
            request.sorting = "feature"

            term = request.terms.add()
            # TODO use a database for this case
            if os.path.exists(upload_path_to_image(q["reference"])):
                term.feature.image.encoded = open(upload_path_to_image(q["reference"]), "rb").read()
            else:
                term.feature.image.id = q["reference"]

            if "features" in q:
                plugins = q["features"]
                if not isinstance(q["features"], (list, set)):
                    plugins = [q["features"]]
                for p in plugins:
                    for k, v in p.items():
                        plugins = term.feature.plugins.add()
                        plugins.name = k.lower()
                        plugins.weight = v

    if "sorting" in data and data["sorting"] == "random":
        request.sorting = "random"

    if "mapping" in data and data["mapping"] == "umap":
        request.mapping = "umap"

    response = stub.search(request)

    return JsonResponse({"status": "ok", "job_id": response.id})


def search_result_view(request):
    #
    # if not request.is_ajax():
    #     return Http404()

    try:
        body = request.body.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        body = request.body

    try:
        data = json.loads(body)
    except Exception as e:
        print("Search: JSON error: {}".format(e))
        return JsonResponse({"status": "error"})

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

    if "id" not in data:
        return JsonResponse({"status": "error"})

    request = indexer_pb2.ListSearchResultRequest(id=data["id"])

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
            print(entry)
            entries.append(entry)
        return JsonResponse({"status": "ok", "entries": entries})
    except grpc.RpcError as e:

        # search is still running
        if e.code() == grpc.StatusCode.FAILED_PRECONDITION:
            return JsonResponse({"status": "running"})

    return JsonResponse({"status": "error"})


def upload(request):
    try:
        if request.method != "POST":
            return JsonResponse({"status": "error"})

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
        return JsonResponse({"status": "error"})
