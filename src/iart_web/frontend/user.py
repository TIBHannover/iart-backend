from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, Http404
from django.conf import settings
from django.contrib import auth
from django.views.decorators.http import require_http_methods

from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token


# def get_csrf_token(request):
#     token = get_token(request)
#     return JsonResponse({"token": token})


@ensure_csrf_cookie
def get_csrf_token(request):
    # token = get_token(request)
    return JsonResponse({"status": "ok"})


@require_http_methods(["POST"])
def login(request):
    print(request.POST)

    if "username" not in request.POST:
        return JsonResponse({"status": "error"})

    if "password" not in request.POST:
        return JsonResponse({"status": "error"})

    username = request.POST["username"]
    password = request.POST["password"]

    if username == "" or password == "":
        return JsonResponse({"status": "error"})

    user = auth.authenticate(username=username, password=password)
    if user is not None:
        auth.login(request, user)

        return JsonResponse({"status": "ok"})

    return JsonResponse({"status": "error"})


@require_http_methods(["POST"])
def register(request):

    if "username" not in request.POST:
        return JsonResponse({"status": "error"})

    if "password" not in request.POST:
        return JsonResponse({"status": "error"})

    if "email" not in request.POST:
        return JsonResponse({"status": "error"})

    username = request.POST["username"]
    password = request.POST["password"]
    email = request.POST["email"]

    if username == "" or password == "" or email == "":
        return JsonResponse({"status": "error"})

    if auth.models.User.objects.filter(username=username).count() > 0:
        return JsonResponse({"status": "error"})

    # TODO Add EMail register here
    user = auth.models.User.objects.create_user(username, email, password)
    user.save()
    user = auth.authenticate(username=username, password=password)

    if user is not None:
        auth.login(request, user)
        return JsonResponse({"status": "ok"})

    return JsonResponse({"status": "error"})


@require_http_methods(["POST"])
def logout(request):
    auth.logout(request)
    return JsonResponse({"status": "ok"})
