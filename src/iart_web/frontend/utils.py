import os

import numpy as np
from django.conf import settings

from pathlib import Path


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


def check_extension(filename: Path, extensions: list):
    if isinstance(filename, str):
        filename = Path(filename)
    extension = "".join(filename.suffixes)
    extension.lower()
    return extension in extensions


def download_file(file, output_dir, output_name=None, max_size=None, extensions=None):
    path = Path(file.name)
    image_ext = "".join(path.suffixes)
    if output_name is not None:
        output_path = os.path.join(output_dir, f"{output_name}{image_ext}")
    else:
        output_path = os.path.join(output_dir, f"{file.name}")

    if extensions is not None:
        if not check_extension(path, extensions):
            return {"status": "error", "error": {"type": "wronge_file_extension"}}
    # TODO add parameter
    if max_size is not None:
        if file.size > max_size:
            return {
                "status": "error",
                "error": {"type": "file_to_large"},
            }

    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, output_path), "wb") as f:

        for i, chunk in enumerate(file.chunks()):
            f.write(chunk)

    return {"status": "ok", "path": Path(output_path)}