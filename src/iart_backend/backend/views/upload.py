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
from backend.models import UploadedImage
from backend.utils import (
    image_normalize,
    image_resize,
    download_url,
    download_file,
    upload_url_to_image,
    upload_url_to_preview,
)


import PIL.Image

PIL.Image.warnings.simplefilter("error", PIL.Image.DecompressionBombError)  # turn off Decompression bomb error
PIL.Image.warnings.simplefilter("error", PIL.Image.DecompressionBombWarning)  # turn off Decompression bomb warning
PIL.Image.MAX_IMAGE_PIXELS = 1000000000  # set max pixel up high

logger = logging.getLogger(__name__)

import PIL.Image

PIL.Image.warnings.simplefilter("error", PIL.Image.DecompressionBombError)  # turn off Decompression bomb error
PIL.Image.warnings.simplefilter("error", PIL.Image.DecompressionBombWarning)  # turn off Decompression bomb warning
PIL.Image.MAX_IMAGE_PIXELS = 1000000000  # set max pixel up high


class Upload(APIView):
    def post(self, request, format=None):
        image_id = uuid.uuid4().hex
        logger.info(
            f"Upload start: request.data.file:'{request.data.get('file')}' request.data.url:'{request.data.get('url')}'"
        )
        if request.data.get("file"):
            tmp_dir = tempfile.mkdtemp()

            print("B", flush=True)
            image_result = download_file(
                output_dir=tmp_dir,
                output_name=image_id,
                file=request.data["file"],
                max_size=20 * 1024 * 1024,
                extensions=(".gif", ".jpg", ".jpeg", ".jpe", ".png", ".tif", ".tiff", ".bmp", ".webp"),
            )
        elif request.data.get("url"):
            tmp_dir = tempfile.mkdtemp()
            image_result = download_url(
                output_dir=tmp_dir,
                output_name=image_id,
                url=request.data["url"],
                max_size=20 * 1024 * 1024,
                extensions=(".gif", ".jpg", ".jpeg", ".jpe", ".png", ".tif", ".tiff", ".bmp", ".webp"),
            )
        else:
            image_result = {
                "status": "error",
                "error": {
                    "type": "unknown_error",
                },
            }

        if image_result["status"] != "ok":
            logger.error(
                f"Upload failed. image_result:'{image_result}' request.data.file:'{request.data.get('file')}' request.data.url:'{request.data.get('url')}'"
            )
            raise APIException(image_result["error"]["type"])

        print("D", flush=True)
        output_dir = os.path.join(
            settings.UPLOAD_ROOT,
            image_id[0:2],
            image_id[2:4],
        )
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, f"{image_id}.{settings.IMAGE_EXT}")

        print("E", flush=True)
        try:
            with Image(filename=image_result["path"]) as img:
                img.format = "jpeg"
                img.save(filename=output_path)

            image = imageio.imread(image_result["path"])
            image = image_normalize(image)
            image = image_resize(image, max_dim=1024)
        except Exception as e:
            logging.error(e)
            logger.error(
                f"Upload failed. image_result:'{image_result}' request.data.file:'{request.data.get('file')}' request.data.url:'{request.data.get('url')}' exception:'{e}'"
            )

            raise APIException("file_is_not_readable")

        try:
            if image is not None:
                imageio.imwrite(output_path, image)

                image_db, created = UploadedImage.objects.get_or_create(
                    name=image_result["origin"],
                    hash_id=image_id,
                )

                return Response(
                    {
                        "entries": [
                            {
                                "id": image_id,
                                "meta": {
                                    "title": image_result["origin"],
                                },
                                "path": upload_url_to_image(image_id),
                                "preview": upload_url_to_image(image_id),
                            }
                        ],
                    }
                )
        except Exception as error:

            logger.error(
                f"Upload failed. image_result:'{image_result}' request.data.file:'{request.data.get('file')}' request.data.url:'{request.data.get('url')}' exception:'{e}'"
            )
            logger.error(traceback.format_exc())

        raise APIException("unknown_error")
