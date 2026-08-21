# ESIEM_CORE

## Vault Prerequisites

ESIEM_CORE uses Docker Swarm secrets for the Vault connection settings.

The following Docker Swarm secrets must exist before deploying the services:

```text
vault_addr
vault_secret_path
vault_token
```

Verify them with:

```bash
docker secret ls
```

Expected secret names:

```text
vault_addr
vault_secret_path
vault_token
```

The Vault connection values are no longer stored in `.env`.

The services receive the secrets through Docker Swarm and access them inside the container as:

```text
/run/secrets/vault_addr
/run/secrets/vault_secret_path
/run/secrets/vault_token
```

The application startup code reads these files and uses them to retrieve application secrets from HashiCorp Vault.

The deployment flow is:

```text
Docker Swarm secret store
        ↓
vault_addr
vault_secret_path
vault_token
        ↓
Docker service
        ↓
/run/secrets/*
        ↓
HashiCorp Vault
```

---

# Starting Elasticsearch

The Elasticsearch stack lives in:

```text
ES/
  docker-stack.bootstrap.yml
  docker-stack.yml
```

## Bootstrap

Use the bootstrap stack for a brand-new deployment or after wiping Elasticsearch data.

Run:

```bash
make network
make validate
make es-dirs
make es-bootstrap
make ps
make logs
```

Verify all Elasticsearch services reach:

```text
REPLICAS   1/1
```

The Elasticsearch stack contains:

```text
ESIEM_CORE_ES_es01
ESIEM_CORE_ES_es02
ESIEM_CORE_ES_es03
```

Once Elasticsearch is running, deploy Kibana:

```bash
make kibana-up
make kibana-ps
make kibana-logs
```

Deploy Logstash:

```bash
make logstash-up
make logstash-ps
make logstash-logs
```

Deploy Scheduler:

```bash
make scheduler-up
make scheduler-ps
make scheduler-logs
```

---

## Normal Start

For an existing Elasticsearch deployment:

```bash
make network
make es-up
make ps
make logs
```

Then start Kibana:

```bash
make kibana-up
make kibana-ps
make kibana-logs
```

Start Logstash:

```bash
make logstash-up
make logstash-ps
make logstash-logs
```

Start Scheduler:

```bash
make scheduler-up
make scheduler-ps
make scheduler-logs
```

---

## Service Status

### Elasticsearch

```bash
make ps
```

Elasticsearch logs:

```bash
make logs
make logs-es02
make logs-es03
```

### Kibana

```bash
make kibana-ps
make kibana-logs
```

### Logstash

```bash
make logstash-ps
make logstash-logs
```

### Scheduler

```bash
make scheduler-ps
make scheduler-logs
```

A healthy Swarm service should show:

```text
REPLICAS   1/1
```

Older `Failed` or `Shutdown` tasks may remain visible in `docker stack ps` after a service has been redeployed. Check the current task and the current replica count.

---

## Current Makefile Limitation

The following Makefile targets still expect:

```text
VAULT_ADDR
VAULT_TOKEN
VAULT_SECRET_PATH
```

to be available as environment variables:

```bash
make wait
make health
make nodes
make shards
make vault-vars
make es-setup
```

These targets should not be used after removing the Vault values from `.env` until they are migrated to the Docker Swarm secret-based workflow.

The Docker services themselves now use:

```text
/run/secrets/vault_addr
/run/secrets/vault_secret_path
/run/secrets/vault_token
```

for Vault access.
