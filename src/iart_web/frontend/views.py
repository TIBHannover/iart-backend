import logging
import sys
import os
import json
import uuid
from urllib.parse import urlparse

import imageio
import numpy as np
import traceback

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, Http404
from django.conf import settings
from django.contrib import auth
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt


# from iart_indexer.database.elasticsearch_database import ElasticSearchDatabase
# from iart_indexer.database.elasticsearch_suggester import ElasticSearchSuggester

import json

from rest_framework import viewsets

if settings.INDEXER_PATH is not None:
    sys.path.append(settings.INDEXER_PATH)


import grpc
from iart_indexer import indexer_pb2, indexer_pb2_grpc
from iart_indexer.utils import meta_from_proto, classifier_from_proto, feature_from_proto, suggestions_from_proto

from .utils import image_normalize
