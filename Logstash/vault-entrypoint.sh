#!/bin/bash
set -euo pipefail

echo "Fetching Logstash secrets from Vault..."

: "${VAULT_ADDR:?VAULT_ADDR is required}"
: "${VAULT_TOKEN:?VAULT_TOKEN is required}"
: "${VAULT_SECRET_PATH:?VAULT_SECRET_PATH is required}"

VAULT_JSON="$(curl -fsS \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  "${VAULT_ADDR}/v1/${VAULT_SECRET_PATH}")"

export ELASTIC_HOST="$(echo "$VAULT_JSON" | jq -r '.data.data.ELASTIC_HOST')"
export ELASTIC_USER="$(echo "$VAULT_JSON" | jq -r '.data.data.ELASTIC_USER')"
export ELASTIC_PASSWORD="$(echo "$VAULT_JSON" | jq -r '.data.data.ELASTIC_PASSWORD')"
export CLIENT_DOMAIN="$(echo "$VAULT_JSON" | jq -r '.data.data.CLIENT_DOMAIN')"
export ROOT_DOMAIN="$(echo "$VAULT_JSON" | jq -r '.data.data.ROOT_DOMAIN')"

if [[ -z "$ELASTIC_HOST" || "$ELASTIC_HOST" == "null" ]]; then
  echo "ELASTIC_HOST missing from Vault"
  exit 1
fi

if [[ -z "$ELASTIC_USER" || "$ELASTIC_USER" == "null" ]]; then
  echo "ELASTIC_USER missing from Vault"
  exit 1
fi

if [[ -z "$ELASTIC_PASSWORD" || "$ELASTIC_PASSWORD" == "null" ]]; then
  echo "ELASTIC_PASSWORD missing from Vault"
  exit 1
fi

echo "Starting Logstash..."

exec /usr/local/bin/docker-entrypoint "$@"