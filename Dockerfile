FROM ubuntu:20.04

RUN DEBIAN_FRONTEND=noninteractive apt update --fix-missing -y
RUN DEBIAN_FRONTEND=noninteractive apt upgrade -y 
RUN DEBIAN_FRONTEND=noninteractive apt install python3-pip npm git -y
RUN DEBIAN_FRONTEND=noninteractive apt install libmariadbclient-dev-compat imagemagick -y

COPY ./policy.xml /etc/ImageMagick-6/policy.xml
COPY ./policy.xml /etc/ImageMagick-6/policy_2.xml

RUN pip install poetry

COPY pyproject.toml poetry.lock /api/
RUN cd /api; poetry export -f requirements.txt > requirements.txt  --without-hashes
RUN cd /api; pip install -r requirements.txt
RUN cd /api; pip install wand

COPY /indexer/pyproject.toml /indexer/poetry.lock /api/indexer/
RUN cd /api/indexer; poetry export -f requirements.txt > requirements.txt
RUN cd /api/indexer; pip install -r requirements.txt

COPY /pyproject.toml /src /api/
COPY /indexer/pyproject.toml /indexer/src /api/indexer/



RUN cd /api; pip install ./indexer
