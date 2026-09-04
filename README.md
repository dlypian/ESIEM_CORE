# ESIEM_CORE

## Vault Prerequisites

ESIEM_CORE uses Docker Swarm secrets for the Vault connection settings.

The following Docker Swarm secrets must exist before deploying the services:

```text
vault_addr
vault_secret_path
vault_token
```

These secrets can now be created through the Makefile.

Create the Vault secrets with:

```bash
make secrets
```

You will be prompted for:

```text
Vault address
Vault secret path
Vault token secret name
Vault token
```

The default Vault token secret name is:

```text
vault_token
```

Unless there is a specific reason to use another name, keep the default so it matches the Docker stack configuration.

After creating the secrets, verify them with:

```bash
make secrets-list
```

or directly with:

```bash
docker secret ls
```

Expected secret names:

```text
vault_addr
vault_secret_path
vault_token
```

The `make secrets` target is safe to run more than once. Existing secrets are detected and are not recreated.

To remove the default Vault Docker Swarm secrets:

```bash
make secrets-remove
```

This removes:

```text
vault_addr
vault_secret_path
vault_token
```

If a custom Vault token secret name was used when running `make secrets`, that custom secret must be removed manually:

```bash
docker secret rm <custom-secret-name>
```

---

## Vault Secret Storage

The Vault connection values are no longer stored in `.env` for the Docker services.

The services receive the Vault connection settings through Docker Swarm secrets and access them inside the containers as:

```text
/run/secrets/vault_addr
/run/secrets/vault_secret_path
/run/secrets/vault_token
```

The application startup code reads these files and uses the values to connect to HashiCorp Vault and retrieve application secrets.

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

# Initial Setup

Before deploying ESIEM_CORE for the first time, create the Docker Swarm network and Vault secrets.

Create the Vault secrets:

```bash
make secrets
```

Verify them:

```bash
make secrets-list
```

Create the shared Docker Swarm network:

```bash
make network
```

Validate the Elasticsearch stack files:

```bash
make validate
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

First make sure the Vault Docker Swarm secrets exist:

```bash
make secrets-list
```

If they do not exist:

```bash
make secrets
```

Then deploy the bootstrap stack:

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

For an existing Elasticsearch deployment, first verify the Vault Docker Swarm secrets:

```bash
make secrets-list
```

If the secrets are missing:

```bash
make secrets
```

Then start Elasticsearch:

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

# Common Deployment Commands

## Vault Secrets

Create Vault Docker Swarm secrets:

```bash
make secrets
```

List Docker Swarm secrets:

```bash
make secrets-list
```

Remove the default Vault Docker Swarm secrets:

```bash
make secrets-remove
```

Direct Docker equivalent:

```bash
docker secret ls
```

---

## Elasticsearch

Deploy the bootstrap stack:

```bash
make es-bootstrap
```

Deploy the normal stack:

```bash
make es-up
```

Show Elasticsearch stack status:

```bash
make ps
```

Show Elasticsearch logs:

```bash
make logs
make logs-es02
make logs-es03
```

Remove the Elasticsearch stack:

```bash
make down
```

---

## Kibana

Start Kibana:

```bash
make kibana-up
```

Show Kibana status:

```bash
make kibana-ps
```

Show Kibana logs:

```bash
make kibana-logs
```

Stop Kibana:

```bash
make kibana-down
```

---

## Logstash

Start Logstash:

```bash
make logstash-up
```

Show Logstash status:

```bash
make logstash-ps
```

Show Logstash logs:

```bash
make logstash-logs
```

Stop Logstash:

```bash
make logstash-down
```

---

## Scheduler

Start Scheduler:

```bash
make scheduler-up
```

Show Scheduler status:

```bash
make scheduler-ps
```

Show Scheduler logs:

```bash
make scheduler-logs
```

Stop Scheduler:

```bash
make scheduler-down
```

---

# Service Status

## Elasticsearch

Show the Elasticsearch services and Swarm tasks:

```bash
make ps
```

Elasticsearch logs:

```bash
make logs
make logs-es02
make logs-es03
```

## Kibana

```bash
make kibana-ps
make kibana-logs
```

## Logstash

```bash
make logstash-ps
make logstash-logs
```

## Scheduler

```bash
make scheduler-ps
make scheduler-logs
```

A healthy Swarm service should show:

```text
REPLICAS   1/1
```

Older `Failed` or `Shutdown` tasks may remain visible in:

```bash
docker stack ps <stack-name>
```

after a service has been redeployed.

Use the current task state and the current replica count to determine whether the service is healthy.

---

# Recommended First-Time Deployment

For a new installation:

```bash
make secrets
make secrets-list

make network
make validate
make es-dirs

make es-bootstrap
make ps
make logs
```

After Elasticsearch is healthy:

```bash
make kibana-up
make logstash-up
make scheduler-up
```

Check all service states:

```bash
make ps
make kibana-ps
make logstash-ps
make scheduler-ps
```

---

# Recommended Normal Startup

For an existing installation:

```bash
make secrets-list

make network
make es-up

make kibana-up
make logstash-up
make scheduler-up
```

Check service states:

```bash
make ps
make kibana-ps
make logstash-ps
make scheduler-ps
```

---

# Vault Secret Troubleshooting

If deployment fails with an error such as:

```text
service es02: secret not found: vault_addr
```

check the Docker Swarm secrets:

```bash
make secrets-list
```

If the expected secrets are missing:

```bash
make secrets
```

Verify that the following names exist:

```text
vault_addr
vault_secret_path
vault_token
```

Then retry the deployment:

```bash
make es-up
```

Docker Swarm secret names must match the names referenced by the Docker stack files exactly.

---

# Current Makefile Limitation

The Docker services use Docker Swarm secrets for Vault connection settings, but several administrative Makefile targets still expect the following values as shell environment variables:

```text
VAULT_ADDR
VAULT_TOKEN
VAULT_SECRET_PATH
```

The affected targets are:

```bash
make wait
make health
make nodes
make shards
make vault-vars
make es-setup
```

These targets currently read the Vault connection information from environment variables rather than directly from Docker Swarm secrets.

If the Vault values have been completely removed from `.env`, these targets will need to be migrated before they can use the same Swarm-secret-only workflow as the Docker services.

The Docker services themselves use:

```text
/run/secrets/vault_addr
/run/secrets/vault_secret_path
/run/secrets/vault_token
```

for Vault access.

---

# Makefile Help

To display the available Makefile targets:

```bash
make help
```

Important setup targets include:

```text
make check-env
make network
make validate

make secrets
make secrets-list
make secrets-remove
```

Important Elasticsearch targets include:

```text
make es-dirs
make es-build
make es-bootstrap
make es-up
make ps
make logs
make logs-es02
make logs-es03
make down
```

Other service targets include:

```text
make kibana-up
make kibana-down
make kibana-ps
make kibana-logs

make logstash-up
make logstash-down
make logstash-ps
make logstash-logs

make scheduler-up
make scheduler-down
make scheduler-ps
make scheduler-logs
```
