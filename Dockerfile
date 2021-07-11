FROM ubuntu:20.10

RUN DEBIAN_FRONTEND=noninteractive apt update --fix-missing -y
RUN DEBIAN_FRONTEND=noninteractive apt upgrade -y 
RUN DEBIAN_FRONTEND=noninteractive apt install python3-pip npm git -y
RUN DEBIAN_FRONTEND=noninteractive apt install libmariadbclient-dev imagemagick -y

RUN pip install poetry

COPY poetry.lock /pyproject.toml /src /api/
COPY /indexer/poetry.lock /indexer/pyproject.toml /indexer/src /api/indexer/


RUN cd /api; pip install ./indexer
RUN cd /api; poetry export -f requirements.txt --output requirements.txt

RUN cd /api; pip install -r requirements.txt
RUN cd /api; pip install wand


#COPY /indexer/pyproject.toml /indexer/src /indexer/
#RUN ls /
#RUN pip install /indexer
# # RUN cd /indexer; poetry install
# RUN cd /web;POETRY_VIRTUALENVS_CREATE=False poetry update; POETRY_VIRTUALENVS_CREATE=False poetry install 
# # RUN cd /web/iart_web/; npm install; npx webpack 


# CMD poetry run python -m iart_web runserver  0.0.0.0:8000




# FROM python:3.8.11-alpine3.13

# RUN apk --update add npm mariadb imagemagick gcc python3-dev linux-headers musl-dev libffi-dev rust cargo libressl-dev git g++ py3-scikit-learn lapack blas py3-cryptography gfortran lapack-dev

# RUN pip install poetry

# COPY poetry.lock /pyproject.toml /src /api/
# COPY /indexer/poetry.lock /indexer/pyproject.toml /indexer/src /api/indexer/


# RUN cd /api; pip install ./indexer
# RUN cd /api; poetry export -f requirements.txt --output requirements.txt

# RUN cd /api; pip install -r requirements.txt
