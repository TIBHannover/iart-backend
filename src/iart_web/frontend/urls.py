from django.contrib import admin
from django.urls import path
from . import views
from . import user

urlpatterns = [
    path("search/", views.search_view, name="search"),
    path("search_result/", views.search_result_view, name="search_result"),
    path("list_features/", views.list_feature_view, name="list_features"),
    path("autocomplete/", views.autocomplete_view, name="autocomplete"),
    path("upload/", views.upload, name="upload"),
    path("login/", user.login, name="login"),
    path("logout/", user.logout, name="logout"),
    path("signup/", user.signup, name="signup"),
    
]
