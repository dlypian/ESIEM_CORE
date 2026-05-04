#!/bin/bash
set -euo pipefail

echo "Fetching Kibana secrets from Vault..."

: "${VAULT_ADDR:?VAULT_ADDR is required}"
: "${VAULT_TOKEN:?VAULT_TOKEN is required}"
: "${VAULT_SECRET_PATH:?VAULT_SECRET_PATH is required}"

NODE_BIN="/usr/share/kibana/node/bin/node"

VAULT_JSON="$(curl -fsS \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  "${VAULT_ADDR}/v1/${VAULT_SECRET_PATH}")"

export ELASTICSEARCH_PASSWORD="$("$NODE_BIN" -e 'const d=JSON.parse(process.argv[1]); console.log(d.data.data.KIBANA_PASSWORD)' "$VAULT_JSON")"
export ELASTICSEARCH_HOSTS="$("$NODE_BIN" -e 'const d=JSON.parse(process.argv[1]); console.log(d.data.data.ELASTIC_HOST)' "$VAULT_JSON")"

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