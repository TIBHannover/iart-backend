import os
import sys
import grpc
import logging

from .utils import RPCView
from django.conf import settings
from django.conf import settings as DjangoSettings
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from frontend.models import UploadedImage, ImageUserRelation
from frontend.utils import (
    media_url_to_image,
    media_url_to_preview,
    upload_url_to_image,
    upload_url_to_preview,
)

if DjangoSettings.INDEXER_PATH is not None:
    sys.path.append(DjangoSettings.INDEXER_PATH)


from iart_indexer import indexer_pb2, indexer_pb2_grpc
from iart_indexer.utils import (
    meta_from_proto,
    classifier_from_proto,
    feature_from_proto,
)

logger = logging.getLogger(__name__)


class Get(RPCView):
    def parse_request(self, params):
        return indexer_pb2.GetRequest(id=params['id'])

    def rpc_get(self, params):
        grpc_request = self.parse_request(params)
        stub = indexer_pb2_grpc.IndexerStub(self.channel)

        try:
            response = stub.get(grpc_request)

            return {
                'entry': {
                    'id': response.id,
                    'meta': meta_from_proto(response.meta),
                    'origin': meta_from_proto(response.origin),
                    'classifier': classifier_from_proto(response.classifier),
                    'feature': feature_from_proto(response.feature),
                    'path': media_url_to_image(response.id),
                    'preview': media_url_to_preview(response.id),
                },
            }

        except grpc.RpcError as error:
            pass

    def post(self, request, format=None):
        result = self.rpc_get(request.data['params'])

        if result is not None:
            return Response(result)

        try:
            hash_id = request.data['params'].get('id')
            image_db = UploadedImage.objects.get(hash_id=hash_id)

            image_path = os.path.join(
                settings.UPLOAD_ROOT,
                image_db.hash_id[0:2],
                image_db.hash_id[2:4],
                f'{image_db.hash_id}.jpg',
            )

            return Response({
                'entry': {
                    'id': hash_id,
                    'meta': [{
                        'name': 'title',
                        'value_str': image_db.name,
                    }],
                    'path': upload_url_to_image(hash_id),
                    'preview': upload_url_to_image(hash_id),
                },
            })
        except UploadedImage.DoesNotExist:
            pass

        raise APIException('unknown_resource')
