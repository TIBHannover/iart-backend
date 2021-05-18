import os
import sys
import json
import uuid
import logging
import traceback

from urllib.parse import urlparse
import imageio

from frontend.utils import image_normalize, upload_url_to_image

from django.views import View
from django.http import HttpResponse, JsonResponse
from django.conf import settings


class Upload(View):
    def post(self, request):
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
