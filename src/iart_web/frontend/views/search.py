import os
import sys
import json
import grpc
import msgpack
import hashlib
import logging

from django.views import View
from django.http import HttpResponse, JsonResponse
from django.conf import settings as DjangoSettings
from django.core.cache import cache
from django.core.exceptions import BadRequest

from iart_indexer import indexer_pb2, indexer_pb2_grpc
from iart_indexer.utils import meta_from_proto, classifier_from_proto, feature_from_proto, suggestions_from_proto

from frontend.models import Image, ImageUserRelation, Collection
from frontend.utils import media_url_to_preview, media_url_to_image
from frontend.utils import RetryOnRpcErrorClientInterceptor, ExponentialBackoff

logger = logging.getLogger(__name__)

if DjangoSettings.INDEXER_PATH is not None:
    sys.path.append(DjangoSettings.INDEXER_PATH)


class Search(View):
    def parse_search_request(self, request, ids=None, collections=None):
        grpc_request = indexer_pb2.SearchRequest()

        weights = {"clip_embedding_feature": 1}
        cluster = {"type": "kmeans", "n": 1}
        lang = request.get("lang", "en")

        if request.get("settings"):
            settings = request["settings"]

            if settings.get("layout"):
                layout = settings["layout"]

                if layout.get("viewType") == "umap":
                    grpc_request.mapping = indexer_pb2.SearchRequest.MAPPING_UMAP

                    if layout.get("viewGrid", False):
                        option = grpc_request.mapping_options.add()
                        option.key = "grid_method"
                        option.string_val = "scipy"
                    else:
                        option = grpc_request.mapping_options.add()
                        option.key = "grid_method"
                        option.string_val = ""

            if settings.get("cluster"):
                if settings["cluster"].get("type"):
                    cluster["type"] = settings["cluster"]["type"]

                if settings["cluster"].get("n"):
                    cluster["n"] = settings["cluster"]["n"]

            if settings.get("weights"):
                weights = settings["weights"]

        if cluster.get("n", 1) > 1:
            if cluster.get("type") == "agglomerative":
                grpc_request.clustering = indexer_pb2.SearchRequest.CLUSTERING_AGGLOMERATIVE
            else:
                grpc_request.clustering = indexer_pb2.SearchRequest.CLUSTERING_KMEANS

            option = grpc_request.clustering_options.add()
            option.key = "k"
            option.int_val = cluster["n"]

        filtered_collections = set()

        if request.get("filters"):
            for k, v in request["filters"].items():
                if not isinstance(v, (list, set)):
                    v = [v]

                for t in v:
                    if isinstance(t, (int, float, str)):
                        t = {"name": t}

                    if k == 'collection' and t.get('hash_id'):
                        filtered_collections.add(t['hash_id'])
                        continue

                    term = grpc_request.terms.add()
                    term.text.field = k
                    term.text.query = t["name"]

                    if t.get("positive", True):
                        term.text.flag = indexer_pb2.NumberSearchTerm.SHOULD
                    else:
                        term.text.flag = indexer_pb2.NumberSearchTerm.NOT

        grpc_request.include_default_collection = True

        if filtered_collections:
            grpc_request.collections.extend(list(filtered_collections))
            grpc_request.include_default_collection = False
        elif collections is not None:
            grpc_request.collections.extend(collections)

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

        if request.get("ids", False):
            request_ids = request["ids"]

            if not isinstance(request_ids, (list, set)):
                request_ids = list(request_ids)

            if ids is not None:
                ids = ids.extend(request_ids)

        if ids is not None:
            grpc_request.ids.extend(ids)

        if request.get("query"):
            for q in request["query"]:
                if q.get("type") == "txt":
                    term = grpc_request.terms.add()
                    term.image_text.query = q["value"]

                    plugins = term.image_text.plugins.add()
                    plugins.name = "clip_embedding_feature"
                    plugins.weight = 1.0
                    # TODO: plugins.lang = lang

                    if q.get("positive", True):
                        term.image_text.flag = indexer_pb2.ImageTextSearchTerm.POSITIVE
                    else:
                        term.image_text.flag = indexer_pb2.ImageTextSearchTerm.NEGATIVE

                elif q.get("type") == "idx":
                    term = grpc_request.terms.add()

                    image_id = q["value"]
                    roi_defined = False

                    if q.get("roi"):
                        roi = q.get("roi")
                        roi_defined = True

                        term.feature.image.roi.x = roi.get("x")
                        term.feature.image.roi.y = roi.get("y")
                        term.feature.image.roi.width = roi.get("width")
                        term.feature.image.roi.height = roi.get("height")

                    image_path = os.path.join(
                        DjangoSettings.UPLOAD_ROOT,
                        image_id[0:2], image_id[2:4],
                        f"{image_id}.jpg",
                    )

                    if os.path.exists(image_path):
                        with open(image_path, "rb") as f:
                            term.feature.image.encoded = f.read()
                    else:
                        # resubmit image from index
                        if roi_defined:
                            image_path = os.path.join(
                                DjangoSettings.MEDIA_ROOT,
                                image_id[0:2], image_id[2:4],
                                f"{image_id}.jpg",
                            )

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

        if request.get("random") and isinstance(request["random"], (int, float, str)):
            grpc_request.sorting = indexer_pb2.SearchRequest.SORTING_RANDOM_FEATURE
            grpc_request.random_seed = str(request["random"])

        return grpc_request

    def rpc_load(self, query, ids=None, collections=None):
        grpc_request = self.parse_search_request(
            query, ids=ids, collections=collections
        )

        grpc_request_bin = grpc_request.SerializeToString()
        grpc_request_hash = hashlib.sha256(grpc_request_bin).hexdigest()

        response_cache = cache.get(grpc_request_hash)

        if response_cache is not None:
            return msgpack.unpackb(response_cache)

        interceptors = (
            RetryOnRpcErrorClientInterceptor(
                max_attempts=4,
                sleeping_policy=ExponentialBackoff(
                    init_backoff_ms=100,
                    max_backoff_ms=1600,
                    multiplier=2,
                ),
                status_for_retry=(grpc.StatusCode.UNAVAILABLE,),
            ),
        )

        channel = grpc.intercept_channel(
            grpc.insecure_channel(
                f"{DjangoSettings.GRPC_HOST}:{DjangoSettings.GRPC_PORT}",
                options=[
                    ("grpc.max_send_message_length", 50 * 1024 * 1024),
                    ("grpc.max_receive_message_length", 50 * 1024 * 1024),
                ],
            ),
            *interceptors,
        )

        stub = indexer_pb2_grpc.IndexerStub(channel)
        response = stub.search(grpc_request)

        cache.set(response.id, grpc_request_hash)

        return {"status": "ok", "job_id": response.id, "state": "pending"}

    def rpc_check_load(self, job_id, collections=None):
        interceptors = (
            RetryOnRpcErrorClientInterceptor(
                max_attempts=4,
                sleeping_policy=ExponentialBackoff(
                    init_backoff_ms=100,
                    max_backoff_ms=1600,
                    multiplier=2,
                ),
                status_for_retry=(grpc.StatusCode.UNAVAILABLE,),
            ),
        )

        channel = grpc.intercept_channel(
            grpc.insecure_channel(
                f"{DjangoSettings.GRPC_HOST}:{DjangoSettings.GRPC_PORT}",
                options=[
                    ("grpc.max_send_message_length", 50 * 1024 * 1024),
                    ("grpc.max_receive_message_length", 50 * 1024 * 1024),
                ],
            ),
            *interceptors,
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
                entry["distance"] = e.distance
                entry["cluster"] = e.cluster
                entry["padded"] = e.padded

                entry["preview"] = media_url_to_preview(e.id)
                entry["path"] = media_url_to_image(e.id)

                entries.append(entry)

            aggregations = []

            for e in response.aggregate:
                aggr = {"field": e.field_name, "entries": []}

                for x in e.entries:
                    aggr["entries"].append({"name": x.key, "count": x.int_val})

                aggregations.append(aggr)

            result = {
                "status": "ok", "entries": entries,
                "aggregations": aggregations, "state": "done",
            }

            request_hash = cache.get(job_id)

            if request_hash is not None:
                cache_data = msgpack.packb(result)
                cache.set(request_hash, msgpack.packb(result))

            return result
        except grpc.RpcError as e:
            # search is still running
            if e.code() == grpc.StatusCode.FAILED_PRECONDITION:
                return {"status": "ok", "job_id": job_id, "state": "pending"}

        return {"status": "error", "state": "done"}

    def add_user_data(self, entries, user):
        ids = [x["id"] for x in entries["entries"]]

        images = ImageUserRelation.objects.filter(image__hash_id__in=ids, user=user)
        user_lut = {x.image.hash_id: {"bookmarked": x.library} for x in images}

        def map_user_data(entry):
            if entry["id"] in user_lut:
                return {**entry, "user": user_lut[entry["id"]]}

            return {**entry, "user": {"bookmarked": False}}

        entries["entries"] = list(map(map_user_data, entries["entries"]))

        return entries

    def post(self, request):
        collections = None

        if request.user.is_authenticated:
            collections = Collection.objects.filter(user=request.user)
            collections = [c.hash_id for c in collections]

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

        if "job_id" in data["params"]:
            response = self.rpc_check_load(data["params"]["job_id"], collections=collections)

            if "entries" in response and request.user.is_authenticated:
                response = self.add_user_data(response, request.user)

            return JsonResponse(response)

        ids = None

        if data["params"].get("bookmarks", False):
            if not request.user.is_authenticated:
                raise BadRequest("not_authenticated")

            image_user_db = ImageUserRelation.objects.filter(user=request.user, library=True)

            ids = [x.image.hash_id for x in image_user_db]

        response = self.rpc_load(data["params"], ids=ids, collections=collections)

        return JsonResponse(response)
