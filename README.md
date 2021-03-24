# Installation

## Required software and tools

- npm
- django
- elasticsearch

## Installation

The first step is to clone the project and load all submodules:

```sh
git clone git@git.tib.eu:iart/web.git
cd web
git submodule init
git submodule update

```

To ensure that the data is retained after the container is finished, local folders must be created and added to the docker-compose.yml file.

```sh
# Local cache for feature dumps
mkdir -p /data/iart/web/cache
# Local path for import msg files
mkdir -p /data/iart/web/dump
# Local path for the elasticsearch database
mkdir -p /data/iart/web/elasticsearch
# Local path for public available images
mkdir -p /data/iart/web/media
# Local path for deep learning models
mkdir -p /data/iart/web/models
# Local path for uploaded images from the user
mkdir -p /data/iart/web/upload
# Local path for feature index
mkdir -p /data/iart/web/faiss
```

Afterwards, the paths in the docker-compose.yml file should be adjusted, for example `/data/iart/web/media/ -> <LOCAL_PATH>/media`. Subsequently, the container can be built and started:

```sh
sudo docker-compose build
sudo docker-compose up
```

## Import data from ARTigo

### Download images

```sh
rsync -azv -e 'ssh -A -J springsteinm@exchange.research.tib.eu' springsteinm@devbox3.research.tib.eu:/nfs/data/iart/web/ ./
tar -xf media.tar.gz -C ./
```

### Import Database

To import data, a snapshot (<DUMP_NAME>.msg) must be stored in the /dump folder and the following command must be executed while the application is running:

```sh
sudo docker-compose exec indexer python -m iart_indexer --m client --task load --dump_path /dump/<DUMP_NAME>.msg
```

### Create retrieval index

To enable the image search, an index with the current database state must be created:

```sh
sudo docker-compose exec indexer python -m iart_indexer --m client --task build_indexer
```

### Generate autocompletion

For the autocomplete to work, it must also be regenerated:

```sh
sudo docker-compose exec indexer python -m iart_indexer --m client --task build_suggester
```

### Generete webpack

```sh
sudo docker-compose exec web npm install
sudo docker-compose exec web npx webpack
```
