import json
import grpc
import sys
import os
import uuid
from django.core.management.base import BaseCommand, CommandError
from django.contrib import auth
from django.conf import settings
from backend.models import Collection, Image

if settings.INDEXER_PATH is not None:
    sys.path.append(settings.INDEXER_PATH)

from iart_indexer import indexer_pb2, indexer_pb2_grpc


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def add_arguments(self, parser):
        parser.add_argument("--user_id", type=str)
        parser.add_argument("--data_path", type=str)
        parser.add_argument("--images_path", type=str)
        parser.add_argument("--collection_name", type=str)
        parser.add_argument("--visibility", type=str, default="user")

    def handle(self, *args, **options):
        user_id = options["user_id"]
        collection_name = options["collection_name"]
        visibility = options["visibility"]

        if visibility.lower() == "user":
            visibility = "U"

        try:
            user_db = auth.models.User.objects.get(id=user_id)
        except auth.models.User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User with id {user_id} doesn't exists"))

        entries = []
        with open(options["data_path"], "r") as f:
            for line in f:
                data =json.loads(line)
                data["path"] = os.path.join(options["images_path"],data["id"][0:2], data["id"][2:4], data["id"]+'.jpg')
                entries.append(data)
        # print(len(entries))
        # print(entries[:2])
        # return 

        collection_db = Collection.objects.create(
            hash_id=uuid.uuid4().hex,
            name=collection_name,
            user=user_db,
            progress=0.0,
            status="U",
            visibility=visibility,
        )
        collection_db.save()
        try:
        
            channel = grpc.insecure_channel(
                f"{settings.GRPC_HOST}:{settings.GRPC_PORT}",
                options=[
                    ("grpc.max_send_message_length", 50 * 1024 * 1024),
                    ("grpc.max_receive_message_length", 50 * 1024 * 1024),
                ],
            )

            stub = indexer_pb2_grpc.IndexerStub(channel)
            def entry_generator(entries, collection_id, collection_name, visibility):
                for i, entry in enumerate(entries):
                    print(i,entry["id"], flush=True)
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
                    if not os.path.exists(entry["path"]):
                        print("skip", flush=True)
                        continue
                    request_image.encoded = open(entry["path"], "rb").read()

                    
                    image_db = Image.objects.create(
                        collection=collection_db,
                        owner=user_db,
                        hash_id=entry["id"],
                    )
                    image_db.save()
                    yield request

            gen_iter = entry_generator(
                entries,
                collection_db.hash_id,
                collection_name,
                visibility,
            )
            count = 0

            # print(next(gen_iter))
            # return
            for i, entry in enumerate(stub.indexing(gen_iter)):
                count += 1

                collection_db.progress = count / len(entries)
                collection_db.save()

            collection_db.progress = 1.0
            if count > 0:
                collection_db.status = "R"
                collection_db.save()

                return {"status": "ok"}
        except:
            collection_db.status = "E"
            collection_db.save()