import os

import numpy as np
from django.conf import settings

from pathlib import Path
import PIL
import requests
from urllib.parse import unquote

import cgi
import mimetypes


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


def image_resize(image, max_dim=None, min_dim=None, size=None):
    if max_dim is not None:
        shape = np.asarray(image.shape[:2], dtype=np.float32)

        long_dim = max(shape)
        scale = min(1, max_dim / long_dim)
        new_shape = np.asarray(shape * scale, dtype=np.int32)

    elif min_dim is not None:
        shape = np.asarray(image.shape[:2], dtype=np.float32)

        short_dim = min(shape)
        scale = min(1, min_dim / short_dim)
        new_shape = np.asarray(shape * scale, dtype=np.int32)
    elif size is not None:
        new_shape = size
    else:
        return image
    img = PIL.Image.fromarray(image)
    img = img.resize(size=new_shape[::-1])
    return np.array(img)


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
    try:
        path = Path(file.name)
        image_ext = "".join(path.suffixes)
        if output_name is not None:
            output_path = os.path.join(output_dir, f"{output_name}{image_ext}")
        else:
            output_path = os.path.join(output_dir, f"{file.name}")

        if extensions is not None:
            if not check_extension(path, extensions):
                return {"status": "error", "error": {"type": "wrong_file_extension"}}
        # TODO add parameter
        if max_size is not None:
            if file.size > max_size:
                return {"status": "error", "error": {"type": "file_too_large"}}

        os.makedirs(output_dir, exist_ok=True)

        with open(os.path.join(output_dir, output_path), "wb") as f:

            for i, chunk in enumerate(file.chunks()):
                f.write(chunk)

        return {"status": "ok", "path": Path(output_path), "origin": file.name}
    except:
        return {"status": "error", "error": {"type": "downloading_error"}}


def download_url(url, output_dir, output_name=None, max_size=None, extensions=None):
    try:
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            print(f"{url} {response.status_code}", flush=True)
            return {"status": "error", "error": {"type": "downloading_error"}}

        print(response.headers, flush=True)

        print("###########################", flush=True)
        params = cgi.parse_header(response.headers.get("Content-Disposition", ""))[-1]
        if "filename" in params:
            filename = os.path.basename(params["filename"])
            ext = "".join(Path(filename).suffixes)
            if extensions is not None:
                if ext not in extensions:

                    return {"status": "error", "error": {"type": "wrong_file_extension"}}

        elif response.headers.get("Content-Type") != None:

            ext = mimetypes.guess_extension(response.headers.get("Content-Type"))
            if ext is None:
                return {"status": "error", "error": {"type": "downloading_error"}}

            if extensions is not None:
                if ext.lower() not in extensions:
                    return {"status": "error", "error": {"type": "wrong_file_extension"}}
            filename = url
        else:
            return {"status": "error", "error": {"type": "file_not_found"}}

        if output_name is not None:
            output_path = os.path.join(output_dir, f"{output_name}{ext}")
        else:
            output_path = os.path.join(output_dir, f"{filename}")

        size = 0
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(1024):
                size += 1024

                if size > max_size:
                    return {"status": "error", "error": {"type": "file_too_large"}}
                f.write(chunk)

        return {"status": "ok", "path": Path(output_path), "origin": filename}
    except:
        return {"status": "error", "error": {"type": "downloading_error"}}


def unflat_dict(data_dict, parse_json=False):
    result_map = {}
    if parse_json:
        data_dict_new = {}
        for k, v in data_dict.items():
            try:
                data = json.loads(v)
                data_dict_new[k] = data
            except:
                data_dict_new[k] = v
        data_dict = data_dict_new
    for k, v in data_dict.items():
        path = k.split(".")
        prev = result_map
        for p in path[:-1]:
            if p not in prev:
                prev[p] = {}
            prev = prev[p]
        prev[path[-1]] = v
    return result_map


def flat_dict(data_dict, parse_json=False):
    result_map = {}
    for k, v in data_dict.items():
        if isinstance(v, dict):
            embedded = flat_dict(v)
            for s_k, s_v in embedded.items():
                s_k = f"{k}.{s_k}"
                if s_k in result_map:
                    logging.error(f"flat_dict: {s_k} alread exist in output dict")

                result_map[s_k] = s_v
            continue

        if k not in result_map:
            result_map[k] = []
        result_map[k] = v
    return result_map


import tarfile
import zipfile


class Archive:
    def __init__(self):
        pass

    def __enter__(self):

        pass

    def __exit__(self):
        pass


class TarArchive(Archive):
    def __init__(self, path):
        self.path = path
        self.f = None

    def __enter__(self):
        self.f = tarfile.open(self.path, mode="r")
        return self

    def members(self):
        if self.f is None:
            return []
        else:
            for info in self.f.getmembers():
                yield info.name

    def read(self, name):
        if self.f is None:
            return None

        try:
            return self.f.extractfile(name).read()
        except KeyError:
            return None

    def __exit__(self, type, value, traceback):
        self.f.close()
        self.f = None


class ZipArchive(Archive):
    def __init__(self, path):
        self.path = path
        self.f = None

    def __enter__(self):
        self.f = zipfile.ZipFile(self.path, "r")
        return self

    def members(self):
        if self.f is None:
            return []
        else:
            for name in self.f.namelist():
                yield name

    def read(self, name):
        if self.f is None:
            return None

        try:
            return self.f.open(name).read()
        except KeyError:
            return None

    def __exit__(self, type, value, traceback):
        self.f.close()
        self.f = None
