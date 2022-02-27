import os
import sys
import json
import uuid
import logging
import imageio
import tempfile
import traceback

from wand.image import Image
from urllib.parse import urlparse
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from frontend.models import UploadedImage
from frontend.utils import (
    image_normalize,
    download_url,
    download_file,
    upload_url_to_image,
    upload_url_to_preview,
)

logger = logging.getLogger(__name__)


class Upload(APIView):
    def post(self, request, format=None):
        image_id = uuid.uuid4().hex

        if request.data.get('file'):
            tmp_dir = tempfile.mkdtemp()

            image_result = download_file(
                output_dir=tmp_dir,
                output_name=image_id,
                file=request.data['file'],
                max_size=5 * 1024 * 1024,
                extensions=(
                    '.gif', '.jpg', '.png',
                    '.tif', '.tiff', '.bmp',
                ),
            )
        elif request.data.get('url'):
            tmp_dir = tempfile.mkdtemp()

            image_result = download_url(
                output_dir=tmp_dir,
                output_name=image_id,
                url=request.data['url'],
                max_size=5 * 1024 * 1024,
                extensions=(
                    '.gif', '.jpg', '.png',
                    '.tif', '.tiff', '.bmp',
                ),
            )
        else:
            image_result = {
                'status': 'error',
                'error': {
                    'type': 'unknown_error',
                },
            }

        if image_result['status'] != 'ok':
            raise APIException(image_result['error']['type'])

        output_dir = os.path.join(
            settings.UPLOAD_ROOT,
            image_id[0:2],
            image_id[2:4],
        )
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, f'{image_id}.jpg')

        try:
            with Image(filename=image_result['path']) as img:
                img.format = 'jpeg'
                img.save(filename=output_path)

            image = imageio.imread(image_result['path'])
            image = image_normalize(image)
        except:
            raise APIException('file_is_not_readable')

        try:
            if image is not None:
                imageio.imwrite(output_path, image)

                image_db, created = UploadedImage.objects.get_or_create(
                    name=image_result['origin'],
                    hash_id=image_id,
                )

                return Response({
                    'entries': [{
                        'id': image_id,
                        'meta': {
                            'title': image_result['origin'],
                        },
                        'path': upload_url_to_image(image_id),
                        'preview': upload_url_to_image(image_id),
                    }],
                })
        except Exception as error:
            logger.error(traceback.format_exc())

        raise APIException('unknown_error')
