from django.contrib import admin
from django.urls import path
from . import views
from . import user

urlpatterns = [
    path("load", views.load, name="load"),
    path("upload", views.upload, name="upload"),
    #
    path("login/", user.login, name="login"),
    path("logout/", user.logout, name="logout"),
    path("signup/", user.signup, name="signup"),
]
