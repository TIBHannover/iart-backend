import os
import sys
import logging
import uuid


from celery import shared_task
from django.contrib.auth.models import User
from frontend.models import Collection

from django.conf import settings

from frontend.utils import TarArchive, ZipArchive, check_extension

if settings.INDEXER_PATH is not None:
    sys.path.append(settings.INDEXER_PATH)
    print('##################################################')
    print('##################################################')
    print('##################################################')
    print(sys.path)

import grpc
from iart_indexer import indexer_pb2, indexer_pb2_grpc
from iart_indexer.utils import meta_from_proto, classifier_from_proto, feature_from_proto, suggestions_from_proto

@shared_task(bind=True)
def collection_upload(self, args):
    print('########################')
    print(args)
    user_id = args.get('user_id')
    collection_name = args.get('collection_name')
    collection_id = args.get('collection_id')
    image_path = args.get('image_path')
    visibility = args.get('visibility')
    entries = args.get('entries')

    # Creating database entry first

    if visibility.lower() == "user":
        visibility = "U"

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return {"status": "error", "error":{"type":"unknown_user"}}  

    collection = Collection.objects.create(name=collection_name, hash_id=collection_id, user=user, progress=0.0, status="U", visibility=visibility)
    collection.save()

    # start indexing

    logging.info(f"Client: Start indexing {len(entries)} images")

    host = settings.GRPC_HOST  # "localhost"
    port = settings.GRPC_PORT  # 50051
    channel = grpc.insecure_channel(
        "{}:{}".format(host, port),
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
        ],
    )

    stub = indexer_pb2_grpc.IndexerStub(channel)

    def entry_generator(entries, archive, collection_id, collection_name, visibility):

        for entry in entries:


            request = indexer_pb2.IndexingRequest()
            request_image = request.image

            request_image.id = uuid.uuid4().hex

            for k, v in entry["meta"].items():

                if isinstance(v, (list, set)):
                    for v_1 in v:
                        meta_field = request_image.meta.add()
                        meta_field.key = k
                        if isinstance(v_1, int):
                            meta_field.int_val = v_1
                        if isinstance(v_1, float):
                            meta_field.float_val = v_1
                        if isinstance(v_1, str):
                            meta_field.string_val = v_1
                else:
                    meta_field = request_image.meta.add()
                    meta_field.key = k
                    if isinstance(v, int):
                        meta_field.int_val = v
                    if isinstance(v, float):
                        meta_field.float_val = v
                    if isinstance(v, str):
                        meta_field.string_val = v

            if "origin" in entry:

                for k, v in entry["origin"].items():

                    if isinstance(v, (list, set)):
                        for v_1 in v:
                            origin_field = request_image.origin.add()
                            origin_field.key = k
                            if isinstance(v_1, int):
                                origin_field.int_val = v_1
                            if isinstance(v_1, float):
                                origin_field.float_val = v_1
                            if isinstance(v_1, str):
                                origin_field.string_val = v_1
                    else:
                        origin_field = request_image.origin.add()
                        origin_field.key = k
                        if isinstance(v, int):
                            origin_field.int_val = v
                        if isinstance(v, float):
                            origin_field.float_val = v
                        if isinstance(v, str):
                            origin_field.string_val = v
            
            collection = request_image.collection
            collection.id = collection_id
            collection.name = collection_name
            collection.is_public = (visibility =="V")
            # print(request_image)
            request_image.encoded = archive.read(entry['path'])
            yield request
        # request_image.path = image.encode()
    if check_extension(image_path,['.zip']):
        archive = ZipArchive(image_path)

    if check_extension(image_path,['.tar', '.tar.gz', '.tar.bz2', '.tar.xz']): 
        archive = TarArchive(image_path)
    
    # gen_iter = entry_generator(entries)
    with archive as ar:
        gen_iter = entry_generator(entries, ar, collection_id, collection_name, visibility)
        # print(next(gen_iter))
        count = 0
        for i, entry in enumerate(stub.indexing(gen_iter)):
            count +=1
        
    # count = 0

    # 
    # try_count = 1
    # while try_count > 0:
    #     try:
            
    #         # print('#####')
    #         # for x in gen_iter:
    #         #     print(x.image.id)
    #         #     blacklist.add(x.image.id)
    #         #     raise
    #         for i, entry in enumerate(stub.indexing(gen_iter)):
    #             # for i, entry in enumerate(entry_generator(entries)):
    #             blacklist.add(entry.id)
    #             count += 1
    #             if count % 1000 == 0:
    #                 speed = count / (time.time() - time_start)
    #                 logging.info(f"Client: Indexing {count}/{len(entries)} speed:{speed}")
    #         try_count = 0
    #     except KeyboardInterrupt:
    #         raise
    #     except Exception as e:
    #         logging.error(e)
    #         try_count -= 1

    return {"status": "error"}
