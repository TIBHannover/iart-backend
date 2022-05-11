import json
import logging
import traceback

from backend.models import Image, ImageUserRelation
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException


class BookmarkAdd(APIView):
    def post(self, request, format=None):
        if not request.user.is_authenticated:
            raise APIException("not_authenticated")

        hash_id = request.data["params"].get("id")

        if hash_id is None:
            raise APIException("unknown_error")

        image, _ = Image.objects.get_or_create(hash_id=hash_id)

        image_user, _ = ImageUserRelation.objects.get_or_create(
            user=request.user,
            image=image,
        )
        image_user.library = True
        image_user.save()

        return Response()


class BookmarkRemove(APIView):
    def post(self, request, format=None):
        if not request.user.is_authenticated:
            raise APIException("not_authenticated")

        hash_id = request.data["params"].get("id")

        if hash_id is None:
            raise APIException("unknown_error")

        image = Image.objects.get(hash_id=hash_id)

        image_user = ImageUserRelation.objects.filter(
            user=request.user,
            image=image,
        )
        image_user.update(library=False)

        return Response()


class BookmarkList(APIView):
    def post(self, request, format=None):
        if not request.user.is_authenticated:
            raise APIException("not_authenticated")

        image_user = ImageUserRelation.objects.filter(
            user=request.user,
            library=True,
        )

        return Response([{"id": x.image.hash_id} for x in image_user])
