#!/bin/bash
set -euo pipefail

echo "Fetching Logstash secrets from Vault..."

: "${VAULT_ADDR:?VAULT_ADDR is required}"
: "${VAULT_TOKEN:?VAULT_TOKEN is required}"
: "${VAULT_SECRET_PATH:?VAULT_SECRET_PATH is required}"

NODE_BIN="/usr/share/logstash/jdk/bin/jshell"

VAULT_JSON="$(ruby -r net/http -r uri -r json -e '
  vault_addr = ENV.fetch("VAULT_ADDR")
  vault_path = ENV.fetch("VAULT_SECRET_PATH")
  vault_token = ENV.fetch("VAULT_TOKEN")

  uri = URI("#{vault_addr}/v1/#{vault_path}")
  req = Net::HTTP::Get.new(uri)
  req["X-Vault-Token"] = vault_token

  http = Net::HTTP.new(uri.host, uri.port)
  http.use_ssl = uri.scheme == "https"

  res = http.request(req)

  unless res.code.to_i.between?(200, 299)
    STDERR.puts "Vault request failed: #{res.code}"
    STDERR.puts res.body
    exit 1
  end

  puts res.body
')"

export ELASTIC_HOST="$(ruby -r json -e 'puts JSON.parse(ARGV[0]).dig("data","data","ELASTIC_HOST")' "$VAULT_JSON")"
export ELASTIC_USER="$(ruby -r json -e 'puts JSON.parse(ARGV[0]).dig("data","data","ELASTIC_USER")' "$VAULT_JSON")"
export ELASTIC_PASSWORD="$(ruby -r json -e 'puts JSON.parse(ARGV[0]).dig("data","data","ELASTIC_PASSWORD")' "$VAULT_JSON")"
export CLIENT_DOMAIN="$(ruby -r json -e 'puts JSON.parse(ARGV[0]).dig("data","data","CLIENT_DOMAIN")' "$VAULT_JSON")"
export ROOT_DOMAIN="$(ruby -r json -e 'puts JSON.parse(ARGV[0]).dig("data","data","ROOT_DOMAIN")' "$VAULT_JSON")"

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