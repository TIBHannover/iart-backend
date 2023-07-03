FROM ubuntu:22.04

RUN DEBIAN_FRONTEND=noninteractive apt update --fix-missing -y
RUN DEBIAN_FRONTEND=noninteractive apt upgrade -y 
RUN DEBIAN_FRONTEND=noninteractive apt install python3-pip npm git -y
RUN DEBIAN_FRONTEND=noninteractive apt install libmariadbclient-dev-compat imagemagick python3-numba python3-opencv python3-psycopg2 python3-numpy python3-imageio -y

COPY ./policy.xml /etc/ImageMagick-6/policy.xml
COPY ./policy.xml /etc/ImageMagick-6/policy_2.xml


RUN pip install django
RUN pip install django-cors-headers
RUN pip install djangorestframework
RUN pip install django-filter
# RUN pip install Markdown
RUN pip install psycopg2-binary
RUN pip install djangorestframework-jwt
RUN pip install python-dateutil
RUN pip install celery
RUN pip install celery[redis]
RUN pip install wand
RUN pip install requests
RUN pip install pymemcache
RUN pip install grpcio 
RUN pip install grpcio-tools
RUN pip install tqdm
RUN pip install msgpack
RUN pip install django_rename_app
RUN pip install gunicorn
RUN pip install mozilla-django-oidc


# RUN pip install poetry

# COPY pyproject.toml poetry.lock /api/
# RUN cd /api; poetry export -f requirements.txt > requirements.txt  --without-hashes
# RUN cd /api; pip install -r requirements.txt
# RUN cd /api; pip install wand
# RUN cd /api; pip install django-rename-app

# COPY /indexer/pyproject.toml /indexer/poetry.lock /api/indexer/
# RUN cd /api/indexer; poetry export -f requirements.txt > requirements.txt
# RUN cd /api/indexer; pip install -r requirements.txt 

COPY /src /app/
# COPY /indexer/src/  /app/

COPY /config.json  /app/

ENV PYTHONPATH=/app
# USER 1000:1000