# ESIEM_CORE

# Starting Elasticsearch

This section explains how to start the Elasticsearch stack in this project.

The Elasticsearch stack lives in:

```text
ES/
  docker-stack.bootstrap.yml
  docker-stack.yml
```

## Bootstrap

Use this for a brand-new deployment or after wiping Elasticsearch data.

```bash
make network
make validate
make es-bootstrap
make wait
make es-setup
make es-up
make wait
make health
make kibana-up
make kibana-ps
make kibana-logs
```

## Normal Start

```bash
make network
make es-up
make wait
make health
make kibana-up
make kibana-ps
make kibana-logs
make logstash-up
make logstash-ps
make logstash-logs
```