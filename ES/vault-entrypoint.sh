#!/bin/bash
set -euo pipefail

echo "Fetching Elasticsearch credentials from Vault..."

: "${VAULT_ADDR:?VAULT_ADDR is required}"
: "${VAULT_TOKEN:?VAULT_TOKEN is required}"
: "${VAULT_SECRET_PATH:?VAULT_SECRET_PATH is required}"

VAULT_JSON="$(curl -fsS \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  "${VAULT_ADDR}/v1/${VAULT_SECRET_PATH}")"

export ELASTIC_USER="$(echo "$VAULT_JSON" | jq -r '.data.data.ELASTIC_USER')"
export ELASTIC_PASSWORD="$(echo "$VAULT_JSON" | jq -r '.data.data.ELASTIC_PASSWORD')"

if [[ -z "${ELASTIC_USER}" || "${ELASTIC_USER}" == "null" ]]; then
  echo "ELASTIC_USER missing from Vault response"
  exit 1
fi

if [[ -z "${ELASTIC_PASSWORD}" || "${ELASTIC_PASSWORD}" == "null" ]]; then
  echo "ELASTIC_PASSWORD missing from Vault response"
  exit 1
fi

echo "Starting Elasticsearch..."

exec /usr/local/bin/docker-entrypoint.sh eswrapper