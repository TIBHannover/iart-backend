import numpy as np
from django.conf import settings


def image_normalize(image):
    if len(image.shape) == 2:

        return np.stack([image] * 3, -1)

    if len(image.shape) == 3:
        if image.shape[-1] == 4:
            return image[..., 0:3]
        if image.shape[-1] == 1:
            return np.concatenate([image] * 3, -1)

    if len(image.shape) == 4:
        return image_normalize(image[0, ...])

    return image


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