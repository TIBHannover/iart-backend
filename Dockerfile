FROM ubuntu:20.10

RUN DEBIAN_FRONTEND=noninteractive apt update -y
RUN DEBIAN_FRONTEND=noninteractive apt upgrade -y 
RUN DEBIAN_FRONTEND=noninteractive apt install python3-pip npm -y

RUN pip install poetry

COPY poetry.lock /pyproject.toml /src /web/
COPY /indexer/poetry.lock /indexer/pyproject.toml /indexer/src /web/indexer/


RUN cd /web; pip install ./indexer
RUN cd /web; poetry export -f requirements.txt --output requirements.txt

RUN cd /web; pip install -r requirements.txt


#COPY /indexer/pyproject.toml /indexer/src /indexer/
#RUN ls /
#RUN pip install /indexer
# # RUN cd /indexer; poetry install
# RUN cd /web;POETRY_VIRTUALENVS_CREATE=False poetry update; POETRY_VIRTUALENVS_CREATE=False poetry install 
# # RUN cd /web/iart_web/; npm install; npx webpack 


# CMD poetry run python -m iart_web runserver  0.0.0.0:8000
