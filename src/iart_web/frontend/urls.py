from django.contrib import admin
from django.urls import path

from iart_web.frontend.views import search
from . import views

urlpatterns = [
    # path("load", views.load, name="load"),
    path("upload", views.Upload.as_view(), name="upload"),
    path("search", views.Search.as_view(), name="search"),
    #
    path("collection_upload", views.CollectionUpload.as_view(), name="collection_upload"),
    path("collection_list", views.CollectionList.as_view(), name="collection_list"),
    path("collection_delete", views.CollectionDelete.as_view(), name="collection_delete"),
    #
    path("get_csrf_token", views.get_csrf_token, name="get_csrf_token"),
    path("login", views.login, name="login"),
    path("logout", views.logout, name="logout"),
    path("register", views.register, name="register"),
    path("get_user", views.GetUser.as_view(), name="get_user"),
    #
    path("add_bookmark", views.BookmarkAdd.as_view(), name="add_bookmark"),
    path("remove_bookmark", views.BookmarkRemove.as_view(), name="remove_bookmark"),
]
