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
        self.f = tarfile.open(self.path, mode='r')
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

    def __exit__(self ,type, value, traceback):
        self.f.close()
        self.f = None


class ZipArchive(Archive):
    def __init__(self, path):
        self.path = path
        self.f = None

    def __enter__(self):
        self.f = zipfile.ZipFile(self.path, 'r')
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
    
    def __exit__(self ,type, value, traceback):
        self.f.close()
        self.f = None
