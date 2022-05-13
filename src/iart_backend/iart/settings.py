"""
Django settings for iart project.

Generated by 'django-admin startproject' using Django 2.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "default_secret"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# FORCE_SCRIPT_NAME = "/"
FORCE_SCRIPT_NAME = "/"

ALLOWED_HOSTS = [
    "iart21.labs.tib.eu",
    "labs.tib.eu/iart",
    "iart01.develop.labs.tib.eu",
    "labs.develop.tib.eu/iart",
    "127.0.0.1",
    "localhost",
]

CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True

INSTALLED_APPS = [
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "backend",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_rename_app",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework.authentication.SessionAuthentication",),
    "EXCEPTION_HANDLER": "backend.exceptions.utils.custom_exception_handler",
}

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "iart.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "iart.wsgi.application"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
        "LOCATION": "127.0.0.1:11211",
        "TIMEOUT": 60 * 60 * 24,
    }
}

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "iart",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "localhost",
        "PORT": 5432,
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{levelname} [{asctime}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "backend.middleware": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
    },
}

# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATICFILES_DIRS = []

STATIC_URL = FORCE_SCRIPT_NAME + "/static/"

MEDIA_ROOT = os.path.join("/data/media/")
UPLOAD_ROOT = os.path.join("/data/upload/")
IMAGE_EXT = "jpg"

MEDIA_URL = FORCE_SCRIPT_NAME + "media/"
UPLOAD_URL = FORCE_SCRIPT_NAME + "upload/"

GRPC_HOST = "localhost"
GRPC_PORT = 50051

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INDEXER_PATH = "/indexer"

# last resolution is used for indexing
IMAGE_RESOLUTIONS = [
    {"min_dim": 200, "suffix": "_m"},
    {"min_dim": 1080, "suffix": ""},
]


import json

config_lut = {
    "secret_key": "SECRET_KEY",
    "force_script_name": "FORCE_SCRIPT_NAME",
    "allowed_hosts": "ALLOWED_HOSTS",
    "debug": "DEBUG",
    "language_code": "LANGUAGE_CODE",
    "static_url": "STATIC_URL",
    "media_root": "MEDIA_ROOT",
    "upload_root": "UPLOAD_ROOT",
    "media_url": "MEDIA_URL",
    "upload_url": "UPLOAD_URL",
    "grpc_host": "GRPC_HOST",
    "grpc_port": "GRPC_PORT",
    "image_resolutions": "IMAGE_RESOLUTIONS",
    "image_ext": "IMAGE_EXT",
}

config_path = os.environ.get("IART_BACKEND_CONFIG")
if config_path is not None and os.path.exists(config_path):
    with open(config_path, "r") as f:
        config = json.load(f)
        for k, v in config.items():
            if k not in config_lut:
                continue
            conf = {config_lut[k]: v}
            globals().update(conf)