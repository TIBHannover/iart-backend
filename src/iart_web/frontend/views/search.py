import os
import sys
import grpc
import msgpack
import hashlib
import logging

from .utils import RPCView
from django.conf import settings as DjangoSettings
from django.db.models import Count
from django.core.cache import cache
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from frontend.models import Image, ImageUserRelation, Collection
from frontend.utils import (
    media_url_to_preview,
    media_url_to_image,
    upload_url_to_preview,
    upload_url_to_image,
)

if DjangoSettings.INDEXER_PATH is not None:
    sys.path.append(DjangoSettings.INDEXER_PATH)


from iart_indexer import indexer_pb2, indexer_pb2_grpc
from iart_indexer.utils import (
    meta_from_proto,
    classifier_from_proto,
    feature_from_proto,
    suggestions_from_proto,
)

from google.protobuf.json_format import MessageToJson

logger = logging.getLogger(__name__)


class Search(RPCView):
    def parse_search_request(self, params, ids=None, collection_ids=None):
        grpc_request = indexer_pb2.SearchRequest()

        weights = {'clip_embedding_feature': 1}
        cluster = {'type': 'kmeans', 'n': 1}
        lang = params.get('lang', 'en')

        if params.get('settings'):
            settings = params['settings']

            if settings.get('layout'):
                layout = settings['layout']

                if layout.get('viewType') == 'umap':
                    grpc_request.mapping = indexer_pb2.SearchRequest.MAPPING_UMAP

                    if layout.get('viewGrid', False):
                        option = grpc_request.mapping_options.add()
                        option.key = 'grid_method'
                        option.string_val = 'scipy'
                    else:
                        option = grpc_request.mapping_options.add()
                        option.key = 'grid_method'
                        option.string_val = ''

            if settings.get('cluster'):
                if settings['cluster'].get('type'):
                    cluster['type'] = settings['cluster']['type']

                if settings['cluster'].get('n'):
                    cluster['n'] = settings['cluster']['n']

            if settings.get('weights'):
                weights = settings['weights']

        if cluster.get('n', 1) > 1:
            if cluster.get('type') == 'agglomerative':
                grpc_request.clustering = indexer_pb2.SearchRequest.CLUSTERING_AGGLOMERATIVE
            elif cluster.get('type') == 'kmeans':
                grpc_request.clustering = indexer_pb2.SearchRequest.CLUSTERING_KMEANS
            else:
                grpc_request.clustering = indexer_pb2.SearchRequest.CLUSTERING_GM

            option = grpc_request.clustering_options.add()
            option.key = 'k'
            option.int_val = cluster['n']

        user_collection_ids = set()

        for k, v in params.get('filters', {}).items():
            if not isinstance(v, (list, set)):
                v = [v]

            for t in v:
                if isinstance(t, (int, float, str)):
                    t = {'name': t}

                if k == 'collection' and t.get('hash_id'):
                    user_collection_ids.add(t['hash_id'])
                    continue

                term = grpc_request.terms.add()
                term.text.field = k
                term.text.query = t['name']

                if t.get('positive', True):
                    term.text.flag = indexer_pb2.NumberSearchTerm.SHOULD
                else:
                    term.text.flag = indexer_pb2.NumberSearchTerm.NOT

        print(f"Search Collections: {user_collection_ids} {collection_ids}", flush=True)
        if user_collection_ids:
            grpc_request.collections.extend(list(user_collection_ids))

            print(f"Search Collections: A", flush=True)
        elif collection_ids is not None:
            grpc_request.collections.extend(collection_ids)
            grpc_request.include_default_collection = True        
            print(f"Search Collections: B", flush=True)
        else:
            grpc_request.include_default_collection = True       
            print(f"Search Collections: C", flush=True)

        for v in params.get('full_text', []):
            term = grpc_request.terms.add()
            term.text.query = v

        if params.get('date_range'):
            date_range = params['date_range']

            if not isinstance(date_range, (list, set)):
                date_range = [date_range]

            if len(date_range) > 1:
                term = grpc_request.terms.add()
                term.number.field = 'meta.yaer_max'
                term.number.int_query = max(date_range)
                term.number.flag = indexer_pb2.NumberSearchTerm.MUST
                term.number.relation = indexer_pb2.NumberSearchTerm.LESS_EQ

            term = grpc_request.terms.add()
            term.number.field = 'meta.year_min'
            term.number.int_query = min(date_range)
            term.number.flag = indexer_pb2.NumberSearchTerm.MUST
            term.number.relation = indexer_pb2.NumberSearchTerm.GREATER_EQ

        for field_name in params.get('aggregate', []):
            grpc_request.aggregate.fields.extend([field_name])
            grpc_request.aggregate.size = 250
            grpc_request.aggregate.use_query = True

        if params.get('ids', False):
            request_ids = params['ids']

            if not isinstance(request_ids, (list, set)):
                request_ids = list(request_ids)

            if ids is not None:
                ids = ids.extend(request_ids)

        if ids is not None:
            grpc_request.ids.extend(ids)

        if params.get('query'):
            for q in params['query']:
                if q.get('type') == 'txt':
                    term = grpc_request.terms.add()
                    term.image_text.query = q['value']

                    plugins = term.image_text.plugins.add()
                    plugins.name = 'clip_embedding_feature'
                    plugins.weight = 1.0
                    # TODO: plugins.lang = lang

                    if q.get('positive', True):
                        term.image_text.flag = indexer_pb2.ImageTextSearchTerm.POSITIVE
                    else:
                        term.image_text.flag = indexer_pb2.ImageTextSearchTerm.NEGATIVE

                elif q.get('type') == 'idx':
                    term = grpc_request.terms.add()

                    image_id = q['value']
                    roi_defined = False

                    if q.get('roi'):
                        roi = q.get('roi')
                        roi_defined = True

                        term.feature.image.roi.x = roi.get('x')
                        term.feature.image.roi.y = roi.get('y')
                        term.feature.image.roi.width = roi.get('width')
                        term.feature.image.roi.height = roi.get('height')

                    image_path = os.path.join(
                        DjangoSettings.UPLOAD_ROOT,
                        image_id[0:2], image_id[2:4],
                        f'{image_id}.jpg',
                    )

                    if os.path.exists(image_path):
                        with open(image_path, 'rb') as f:
                            term.feature.image.encoded = f.read()
                    else:
                        # resubmit image from index
                        if roi_defined:
                            image_path = os.path.join(
                                DjangoSettings.MEDIA_ROOT,
                                image_id[0:2], image_id[2:4],
                                f'{image_id}.jpg',
                            )

                            if os.path.exists(image_path):
                                with open(image_path, 'rb') as f:
                                    term.feature.image.encoded = f.read()
                        else:
                            term.feature.image.id = q['value']

                    if q.get('weights'):
                        for k, v in q['weights'].items():
                            plugins = term.feature.plugins.add()
                            plugins.name = k.lower()
                            plugins.weight = v
                    else:
                        for k, v in weights.items():
                            plugins = term.feature.plugins.add()
                            plugins.name = k.lower()
                            plugins.weight = v

                    if q.get('positive', True):
                        term.feature.flag = indexer_pb2.ImageTextSearchTerm.POSITIVE
                    else:
                        term.feature.flag = indexer_pb2.ImageTextSearchTerm.NEGATIVE

                grpc_request.sorting = indexer_pb2.SearchRequest.SORTING_FEATURE

        if params.get('random') and isinstance(params['random'], (int, float, str)):
            grpc_request.sorting = indexer_pb2.SearchRequest.SORTING_RANDOM_FEATURE
            grpc_request.random_seed = str(params['random'])

        return grpc_request

    def rpc_load(self, params, ids=None, collection_ids=None):
        grpc_request = self.parse_search_request(
            params,
            ids=ids,
            collection_ids=collection_ids,
        )
        logger.info(f"Search::rpc_load parse_search_request:'{MessageToJson(grpc_request)}'")

        grpc_request_bin = grpc_request.SerializeToString()
        grpc_request_hash = hashlib.sha256(grpc_request_bin).hexdigest()

        response_cache = cache.get(grpc_request_hash)

        if response_cache is not None:
            return msgpack.unpackb(response_cache)

        stub = indexer_pb2_grpc.IndexerStub(self.channel)
        response = stub.search(grpc_request)

        cache.set(response.id, grpc_request_hash)

        return {'job_id': response.id}

    def rpc_check_load(self, job_id, collections=None):
        stub = indexer_pb2_grpc.IndexerStub(self.channel)
        request = indexer_pb2.ListSearchResultRequest(id=job_id)

        try:
            response = stub.list_search_result(request)

            if collections is not None:
                collection_ids = [c['hash_id'] for c in collections]
            else:
                collection_ids = []

            entries = []

            for e in response.entries:
                entry = {
                    'id': e.id,
                    'meta': meta_from_proto(e.meta),
                    'origin': meta_from_proto(e.origin),
                    'classifier': classifier_from_proto(e.classifier),
                    'feature': feature_from_proto(e.feature),
                    'coordinates': list(e.coordinates),
                    'distance': e.distance,
                    'cluster': e.cluster,
                    'padded': e.padded,
                }

                entry['collection'] = {
                    'id': e.collection.id,
                    'name': e.collection.name,
                    'is_public': e.collection.is_public,
                    'user': e.collection.id in collection_ids,
                }

                if e.collection.id in collection_ids:
                    entry['path'] = upload_url_to_image(e.id)
                    entry['preview'] = upload_url_to_image(e.id)
                else:
                    entry['path'] = media_url_to_image(e.id)
                    entry['preview'] = media_url_to_preview(e.id)

                entries.append(entry)

            aggregations = []

            for e in response.aggregate:
                aggr = {
                    'field': e.field_name,
                    'entries': [],
                }

                for x in e.entries:
                    aggr['entries'].append({
                        'name': x.key,
                        'count': x.int_val,
                    })

                aggregations.append(aggr)

            if collections:
                aggregations.append({
                    'field': 'collection',
                    'entries': collections,
                })

            result = {
                'entries': entries,
                'aggregations': aggregations,
            }

            request_hash = cache.get(job_id)

            if request_hash is not None:
                cache_data = msgpack.packb(result)
                cache.set(request_hash, msgpack.packb(result))

            return result
        except grpc.RpcError as error:
            if error.code() == grpc.StatusCode.FAILED_PRECONDITION:
                return {'job_id': job_id}
            else:
                logger.error(f"Search::rpc_check_load exception:'{error}'")
        except Exception as e:
            logger.error(f"Search::rpc_check_load exception:'{e}'")

        return None

    def add_user_data(self, result, user):
        images = ImageUserRelation.objects.filter(
            image__hash_id__in=[x['id'] for x in result['entries']],
            user=user,
        )
        user_lut = {x.image.hash_id: {'bookmarked': x.library} for x in images}

        def map_data(entry):
            return {
                **entry,
                'user': user_lut.get(entry['id'], {'bookmarked': False})
            }

        result['entries'] = list(map(map_data, result['entries']))

        return result

    def post(self, request, format=None):
        params = request.data['params']
        collections = None
        
        if request.user.is_authenticated:
            collections = [
                {
                    'hash_id': collection.hash_id,
                    'name': collection.name,
                    'count': collection.count,
                }
                for collection in Collection.objects \
                    .filter(user=request.user) \
                    .annotate(count=Count('image'))
            ]

        if params.get('job_id'):
            result = self.rpc_check_load(params['job_id'], collections)

            if result is None:
                raise APIException('unknown_error')

            if result.get('entries') and request.user.is_authenticated:
                result = self.add_user_data(result, request.user)


            return Response(result)

        image_ids = None
        collection_ids = None

        if params.get('bookmarks', False):
            if not request.user.is_authenticated:
                raise APIException('not_authenticated')

            image_user_db = ImageUserRelation.objects.filter(
                user=request.user,
                library=True,
            )
            image_ids = [x.image.hash_id for x in image_user_db]

        if collections:
            collection_ids = [c['hash_id'] for c in collections]
            
        result = self.rpc_load(params, image_ids, collection_ids)

        if result is None:
            raise APIException('unknown_error')

        return Response(result)
