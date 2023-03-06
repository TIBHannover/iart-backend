import os
import sys
import grpc
import uuid
import imageio
import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import BadRequest
from backend.models import Collection, Image
from backend.utils import TarArchive, ZipArchive, check_extension

from iart_indexer import indexer_pb2, indexer_pb2_grpc
from iart_indexer.utils import image_resize

if settings.INDEXER_PATH is not None:
    sys.path.append(settings.INDEXER_PATH)

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def collection_upload(self, args):
    user_id = args.get("user_id")
    collection_name = args.get("collection_name")
    collection_id = args.get("collection_id")
    image_path = args.get("image_path")
    visibility = args.get("visibility")
    entries = args.get("entries")

    if visibility.lower() == "user":
        visibility = "U"

    try:
        user = get_user_model().objects.get(pk=user_id)
    except get_user_model().DoesNotExist:
        raise BadRequest("unknown_user")

    collection = Collection.objects.create(
        name=collection_name,
        hash_id=collection_id,
        user=user,
        progress=0.0,
        status="U",
        visibility=visibility,
    )
    collection.save()

    logger.info(f"Client: Start indexing {len(entries)} images")

    channel = grpc.insecure_channel(
        f"{settings.GRPC_HOST}:{settings.GRPC_PORT}",
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
        ],
    )

    stub = indexer_pb2_grpc.IndexerStub(channel)

    def entry_generator(entries, collection_id, collection_name, visibility):
        for entry in entries:
            request = indexer_pb2.IndexingRequest()
            request_image = request.image
            request_image.id = entry["id"]

            for k, v in entry.get("meta", {}).items():
                if isinstance(v, (list, set)):
                    for v_1 in v:
                        meta_field = request_image.meta.add()
                        meta_field.key = k

                        if isinstance(v_1, int):
                            meta_field.int_val = v_1
                        elif isinstance(v_1, float):
                            meta_field.float_val = v_1
                        elif isinstance(v_1, str):
                            meta_field.string_val = v_1
                else:
                    meta_field = request_image.meta.add()
                    meta_field.key = k

                    if isinstance(v, int):
                        meta_field.int_val = v
                    elif isinstance(v, float):
                        meta_field.float_val = v
                    elif isinstance(v, str):
                        meta_field.string_val = v

            for k, v in entry.get("origin", {}).items():
                if isinstance(v, (list, set)):
                    for v_1 in v:
                        origin_field = request_image.origin.add()
                        origin_field.key = k

                        if isinstance(v_1, int):
                            origin_field.int_val = v_1
                        elif isinstance(v_1, float):
                            origin_field.float_val = v_1
                        elif isinstance(v_1, str):
                            origin_field.string_val = v_1
                else:
                    origin_field = request_image.origin.add()
                    origin_field.key = k

                    if isinstance(v, int):
                        origin_field.int_val = v
                    elif isinstance(v, float):
                        origin_field.float_val = v
                    elif isinstance(v, str):
                        origin_field.string_val = v

            collection = request_image.collection
            collection.id = collection_id
            collection.name = collection_name
            collection.is_public = visibility == "V"

            request_image.encoded = open(entry["path"], "rb").read()

            yield request

    if check_extension(image_path, [".zip"]):
        archive = ZipArchive(image_path)
    elif check_extension(image_path, [".tar", ".tar.gz", ".tar.bz2", ".tar.xz"]):
        archive = TarArchive(image_path)

    new_entries = []

    with archive as ar:
        for entry in entries:
            image = imageio.imread(archive.read(entry["path"]))
            hash_value = uuid.uuid4().hex
            image_output_file = None

            for res in settings.IMAGE_RESOLUTIONS:
                min_size = res.get("min_size", 200)
                suffix = res.get("suffix", "")
                new_image = image_resize(image, min_dim=min_size)

                image_output_dir = os.path.join(settings.UPLOAD_ROOT, hash_value[0:2], hash_value[2:4])
                os.makedirs(image_output_dir, exist_ok=True)
                image_output_file = os.path.join(image_output_dir, f"{hash_value}{suffix}.jpg")

                logger.info(f"Client: Created image {image_output_file}")
                imageio.imwrite(image_output_file, new_image)

            if image_output_file is not None:
                new_entries.append(
                    {
                        **entry,
                        "id": hash_value,
                        "path": image_output_file,
                    }
                )

                image_db = Image.objects.create(
                    collection=collection,
                    owner=user,
                    hash_id=hash_value,
                )
                image_db.save()

    if len(new_entries) == 0:
        collection.status = "E"
        collection.save()

        raise BadRequest("no_uploaded_images")

    gen_iter = entry_generator(
        new_entries,
        collection_id,
        collection_name,
        visibility,
    )
    count = 0

    for i, entry in enumerate(stub.indexing(gen_iter)):
        count += 1

        collection.progress = count / len(entries)
        collection.save()

    if len(entries) == count:
        collection.status = "R"
        collection.save()

        return {"status": "ok"}

    collection.status = "E"
    collection.save()

    raise BadRequest()
