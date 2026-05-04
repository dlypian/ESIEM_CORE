#!/bin/bash
set -euo pipefail

echo "Fetching Kibana secrets from Vault..."

: "${VAULT_ADDR:?VAULT_ADDR is required}"
: "${VAULT_TOKEN:?VAULT_TOKEN is required}"
: "${VAULT_SECRET_PATH:?VAULT_SECRET_PATH is required}"

VAULT_JSON="$(curl -fsS \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  "${VAULT_ADDR}/v1/${VAULT_SECRET_PATH}")"

export ELASTICSEARCH_PASSWORD="$(echo "$VAULT_JSON" | jq -r '.data.data.KIBANA_PASSWORD')"
export ELASTICSEARCH_HOSTS="$(echo "$VAULT_JSON" | jq -r '.data.data.ELASTIC_HOST')"

if [[ -z "$ELASTICSEARCH_PASSWORD" || "$ELASTICSEARCH_PASSWORD" == "null" ]]; then
  echo "KIBANA_PASSWORD missing from Vault"
  exit 1
fi

if [[ -z "$ELASTICSEARCH_HOSTS" || "$ELASTICSEARCH_HOSTS" == "null" ]]; then
  echo "ELASTIC_HOST missing from Vault"
  exit 1
fi

echo "Starting Kibana..."

exec /usr/local/bin/kibana-docker