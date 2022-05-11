from django.urls import path
from . import views

urlpatterns = [
    path("get", views.Get.as_view(), name="get"),
    path("upload", views.Upload.as_view(), name="upload"),
    path("search", views.Search.as_view(), name="search"),
    #
    path("add_collection", views.CollectionAdd.as_view(), name="add_collection"),
    path("remove_collection", views.CollectionRemove.as_view(), name="remove_collection"),
    path("list_collection", views.CollectionList.as_view(), name="list_collection"),
    #
    path("get_csrf_token", views.get_csrf_token, name="get_csrf_token"),
    path("get_user", views.User.as_view(), name="user"),
    path("login", views.Login.as_view(), name="login"),
    path("logout", views.Logout.as_view(), name="logout"),
    path("register", views.Register.as_view(), name="register"),
    #
    path("add_bookmark", views.BookmarkAdd.as_view(), name="add_bookmark"),
    path("remove_bookmark", views.BookmarkRemove.as_view(), name="remove_bookmark"),
    path("list_bookmark", views.BookmarkList.as_view(), name="list_bookmark"),
]
