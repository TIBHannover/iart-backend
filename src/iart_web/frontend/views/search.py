import os
import sys
import json

from django.views import View
from django.http import HttpResponse, JsonResponse
from django.conf import settings

if settings.INDEXER_PATH is not None:
    sys.path.append(settings.INDEXER_PATH)
    print(sys.path)

import grpc
from iart_indexer import indexer_pb2, indexer_pb2_grpc
from iart_indexer.utils import meta_from_proto, classifier_from_proto, feature_from_proto, suggestions_from_proto


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


class Search(View):
    def parse_search_request(self, request):
        grpc_request = indexer_pb2.SearchRequest()
        weights = {"clip_embedding_feature": 1}

        if request.get("settings"):
            if request["settings"].get("layout") == "umap":
                grpc_request.mapping = "umap"

            if request["settings"].get("weights"):
                weights = request["settings"]["weights"]

        if request.get("filters"):
            for k, v in request["filters"].items():
                if not isinstance(v, (list, set)):
                    v = [v]
                for t in v:
                    term = grpc_request.terms.add()
                    term.text.field = k
                    term.text.query = t

        if request.get("full_text"):
            for v in request["full_text"]:
                term = grpc_request.terms.add()
                term.text.query = v

        if request.get("date_range"):
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

        if request.get("aggregate"):
            for field_name in request["aggregate"]:
                grpc_request.aggregate.fields.extend([field_name])
                grpc_request.aggregate.size = 250

        if request.get("query"):
            for q in request["query"]:
                if q.get("type") == "txt":
                    print(q, flush=True)
                    term = grpc_request.terms.add()
                    term.image_text.query = q["value"]

                    plugins_defined = False
                    if q.get("weights"):
                        for k, v in q["weights"].items():
                            plugins_defined = True
                            plugins = term.image_text.plugins.add()
                            plugins.name = k.lower()
                            plugins.weight = v
                    else:
                        for k, v in weights.items():
                            plugins_defined = True
                            plugins = term.image_text.plugins.add()
                            plugins.name = k.lower()
                            plugins.weight = v

                    # Fallback if weights are defined but no plugins
                    if not plugins_defined:
                        plugins = term.image_text.plugins.add()
                        plugins.name = "clip_embedding_feature"
                        plugins.weight = 1.0

                    if q.get("positive", True):
                        term.image_text.flag = indexer_pb2.ImageTextSearchTerm.POSITIVE
                    else:
                        term.image_text.flag = indexer_pb2.ImageTextSearchTerm.NEGATIVE

                elif q.get("type") == "idx":
                    term = grpc_request.terms.add()

                    # check if image exists in upload folder
                    image_id = q["value"]
                    image_path = os.path.join(settings.UPLOAD_ROOT, image_id[0:2], image_id[2:4], f"{image_id}.jpg")
                    if os.path.exists(image_path):
                        with open(image_path, "rb") as f:
                            term.feature.image.encoded = f.read()
                    else:
                        term.feature.image.id = q["value"]

                    if q.get("weights"):
                        for k, v in q["weights"].items():
                            plugins = term.feature.plugins.add()
                            plugins.name = k.lower()
                            plugins.weight = v
                    else:
                        for k, v in weights.items():
                            plugins = term.feature.plugins.add()
                            plugins.name = k.lower()
                            plugins.weight = v

                    if q.get("positive", True):
                        term.feature.flag = indexer_pb2.ImageTextSearchTerm.POSITIVE
                    else:
                        term.feature.flag = indexer_pb2.ImageTextSearchTerm.NEGATIVE

                grpc_request.sorting = indexer_pb2.SearchRequest.SORTING_FEATURE

        if request.get("random"):
            if isinstance(request["random"], (int, float, str)):
                # old behaviour
                # grpc_request.sorting = indexer_pb2.SearchRequest.SORTING_RANDOM
                grpc_request.sorting = indexer_pb2.SearchRequest.SORTING_RANDOM_FEATURE
                grpc_request.random_seed = str(request["random"])

        return grpc_request

    def rpc_load(self, query):

        grpc_request = self.parse_search_request(query)

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

    def rpc_check_load(self, job_id):

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

    def post(self, request):
        try:
            body = request.body.decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            body = request.body

        try:
            data = json.loads(body)
        except Exception as e:
            print("Search: JSON error: {}".format(e))
            return JsonResponse({"status": "error"})

        print(f"Data: {data}", flush=True)
        if "params" not in data:
            return JsonResponse({"status": "error"})

        # Check for existing search job
        if "job_id" in data["params"]:
            response = self.rpc_check_load(data["params"]["job_id"])
            return JsonResponse(response)
        # Should a new search request
        response = self.rpc_load(data["params"])

        return JsonResponse(response)
