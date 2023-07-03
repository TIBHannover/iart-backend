import logging
import traceback

from django.contrib import auth
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException


@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({})


class User(APIView):
    def post(self, request, format=None):
        if not request.user.is_authenticated:
            raise APIException('not_authenticated')

        try:
            user = request.user

            return Response({
                'username': user.get_username(),
                'email': user.email,
                'date': user.date_joined,
            })
        except Exception as e:
            logging.error(traceback.format_exc())

        raise APIException('unknown_user')


class Login(APIView):
    def post(self, request, format=None):
        username = request.data['params'].get('name')
        password = request.data['params'].get('password')

        if not username:
            raise APIException('username_not_provided')

        if not password:
            raise APIException('password_not_provided')

        user = auth.authenticate(username=username, password=password)

        if user is not None:
            auth.login(request, user)

            return Response({
                'username': user.get_username(),
                'email': user.email,
                'date_joined': user.date_joined,
            })

        raise APIException('unknown_user')


class Logout(APIView):
    def post(self, request, format=None):
        auth.logout(request)

        return Response()


class Register(APIView):
    def post(self, request, format=None):
        username = request.data['params'].get('name')
        password = request.data['params'].get('password')
        email = request.data['params'].get('email')

        if not username:
            raise APIException('username_not_provided')

        if not password:
            raise APIException('password_not_provided')

        if not email:
            raise APIException('email_not_provided')

        if get_user_model().objects.filter(username=username).count() > 0:
            raise APIException('username_already_taken')

        user = get_user_model().objects.create_user(username, email, password)
        user.save()
        user = auth.authenticate(username=username, password=password)

        if user is not None:
            auth.login(request, user)

            return Response({
                'username': user.get_username(),
                'email': user.email,
                'date_joined': user.date_joined,
            })

        raise APIException('unknown_user')
