# ESIEM_CORE

# Starting Elasticsearch

This section explains how to start the Elasticsearch stack in this project.

The Elasticsearch stack lives in:

```text
ES/
  docker-stack.bootstrap.yml
  docker-stack.yml


## Bootstrap

make network
make validate
make bootstrap
make wait
make health
make up
make wait
make health

## Normal Start

make up
make wait
make health