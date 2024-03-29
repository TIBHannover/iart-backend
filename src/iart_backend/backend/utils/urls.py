import os

from django.conf import settings


def media_url_to_image(id):
    return f"{settings.MEDIA_URL}{id[0:2]}/{id[2:4]}/{id}.{settings.IMAGE_EXT}"


def media_url_to_preview(id):
    return f"{settings.MEDIA_URL}{id[0:2]}/{id[2:4]}/{id}_m.{settings.IMAGE_EXT}"


def upload_url_to_image(id):
    print(f"{settings.UPLOAD_URL}{id[0:2]}/{id[2:4]}/{id}.{settings.IMAGE_EXT}")
    return f"{settings.UPLOAD_URL}{id[0:2]}/{id[2:4]}/{id}.{settings.IMAGE_EXT}"


def upload_url_to_preview(id):
    print(f"{settings.UPLOAD_URL}{id[0:2]}/{id[2:4]}/{id}_m.{settings.IMAGE_EXT}")
    return f"{settings.UPLOAD_URL}{id[0:2]}/{id[2:4]}/{id}_m.{settings.IMAGE_EXT}"


def upload_path_to_image(id):
    return os.path.join(settings.UPLOAD_ROOT, id[0:2], id[2:4], f"{id}.{settings.IMAGE_EXT}")
