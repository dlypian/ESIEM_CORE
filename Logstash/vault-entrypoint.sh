#!/bin/bash
set -euo pipefail

echo "Fetching Logstash secrets from Vault..."

: "${VAULT_ADDR:?VAULT_ADDR is required}"
: "${VAULT_TOKEN:?VAULT_TOKEN is required}"
: "${VAULT_SECRET_PATH:?VAULT_SECRET_PATH is required}"

VAULT_JSON="$(curl -fsS \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  "${VAULT_ADDR}/v1/${VAULT_SECRET_PATH}")"

json_get() {
  local key="$1"
  echo "$VAULT_JSON" | sed -n "s/.*\"${key}\":\"\\([^\"]*\\)\".*/\\1/p"
}

export ELASTIC_HOST="$(json_get ELASTIC_HOST)"
export ELASTIC_USER="$(json_get ELASTIC_USER)"
export ELASTIC_PASSWORD="$(json_get ELASTIC_PASSWORD)"
export CLIENT_DOMAIN="$(json_get CLIENT_DOMAIN)"
export ROOT_DOMAIN="$(json_get ROOT_DOMAIN)"

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