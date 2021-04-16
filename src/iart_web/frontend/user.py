from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, Http404
from django.conf import settings
from django.contrib import auth
from django.views.decorators.http import require_http_methods

from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token
import logging
import json


# def get_csrf_token(request):
#     token = get_token(request)
#     return JsonResponse({"token": token})


@ensure_csrf_cookie
def get_csrf_token(request):
    # token = get_token(request)
    return JsonResponse({"status": "ok"})


@require_http_methods(["POST"])
def login(request):
    try:
        body = request.body.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        body = request.body

    try:
        data = json.loads(body)
    except Exception as e:
        print("Search: JSON error: {}".format(e), flush=True)
        return JsonResponse({"status": "error"})

    if "name" not in data["params"]:
        print("name", flush=True)
        return JsonResponse({"status": "error"})

    if "password" not in data["params"]:
        print("password", flush=True)
        return JsonResponse({"status": "error"})

    username = data["params"]["name"]
    password = data["params"]["password"]

    if username == "" or password == "":
        return JsonResponse({"status": "error"})

    user = auth.authenticate(username=username, password=password)
    if user is not None:
        auth.login(request, user)

        return JsonResponse({"status": "ok", "data": {"username": user.get_username()}})

    return JsonResponse({"status": "error"})


@require_http_methods(["POST"])
def register(request):
    try:
        body = request.body.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        body = request.body

    try:
        data = json.loads(body)
    except Exception as e:
        print("Search: JSON error: {}".format(e), flush=True)
        return JsonResponse({"status": "error"})

    print(data, flush=True)
    if "name" not in data["params"]:
        print("name", flush=True)
        return JsonResponse({"status": "error"})

    if "password" not in data["params"]:
        print("password", flush=True)
        return JsonResponse({"status": "error"})

    if "email" not in data["params"]:
        print("email", flush=True)
        return JsonResponse({"status": "error"})

    username = data["params"]["name"]
    password = data["params"]["password"]
    email = data["params"]["email"]

    if username == "" or password == "" or email == "":
        print("check1", flush=True)
        return JsonResponse({"status": "error"})

    if auth.models.User.objects.filter(username=username).count() > 0:
        print("check2", flush=True)
        return JsonResponse({"status": "error"})

    # TODO Add EMail register here
    user = auth.models.User.objects.create_user(username, email, password)
    user.save()
    user = auth.authenticate(username=username, password=password)

    if user is not None:
        auth.login(request, user)
        return JsonResponse({"status": "ok"})

    print("check3", flush=True)
    return JsonResponse({"status": "error"})


@require_http_methods(["POST"])
def logout(request):
    auth.logout(request)
    return JsonResponse({"status": "ok"})
