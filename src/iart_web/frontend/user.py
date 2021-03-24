from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, Http404
from django.conf import settings
from django.contrib import auth
from django.views.decorators.http import require_http_methods


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
def signup(request):

    if "username" not in request.POST:
        return JsonResponse({"status": "error"})

    if "password" not in request.POST:
        return JsonResponse({"status": "error"})

    username = request.POST["username"]
    password = request.POST["password"]

    if username == "" or password == "":
        return JsonResponse({"status": "error"})

    if auth.models.User.objects.filter(username=username).count() > 0:
        return JsonResponse({"status": "error"})

    # TODO Add EMail signup here
    user = auth.models.User.objects.create_user(username, "n@n.n", password)
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
