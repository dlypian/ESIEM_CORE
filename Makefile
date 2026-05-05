SHELL := /bin/bash
.ONESHELL:
.DEFAULT_GOAL := help

ENV_FILE := .env

ES_BOOTSTRAP_STACK := ES/docker-stack.bootstrap.yml
ES_STACK := ES/docker-stack.yml
STACK_NAME := ESIEM_CORE_ES
NETWORK_NAME := ESIEM_Network
ES_IMAGE_NAME := esiem/elasticsearch-vault
MGMT_IMAGE_NAME := esiem/mgmt-setup
KIBANA_STACK_NAME := ESIEM_CORE_KIBANA
KIBANA_STACK := Kibana/docker-stack.yml
KIBANA_IMAGE_NAME := esiem/kibana-vault
LOGSTASH_STACK_NAME := ESIEM_CORE_LOGSTASH
LOGSTASH_STACK := Logstash/docker-stack.yml
LOGSTASH_IMAGE_NAME := esiem/logstash-vault
SCHEDULER_STACK_NAME := ESIEM_CORE_SCHEDULER
SCHEDULER_STACK := Scheduler/docker-stack.yml
SCHEDULER_IMAGE_NAME := esiem/scheduler-vault


VAULT_GET_PY := python3 -c 'import json,sys; d=json.load(sys.stdin)["data"]["data"]; print(d["ELASTIC_PASSWORD"])'

-include $(ENV_FILE)
export $(shell sed -n 's/^\([A-Za-z_][A-Za-z0-9_]*\)=.*/\1/p' $(ENV_FILE) 2>/dev/null)

ES_URL := https://localhost:9200

.PHONY: help check-env network validate es-bootstrap es-up wait health nodes shards down ps logs logs-es02 logs-es03 clean-history es-build vault-vars mgmt-build es-setup kibana-build kibana-up kibana-down kibana-ps kibana-logs logstash-build logstash-up logstash-down logstash-ps logstash-logs scheduler-build scheduler-up scheduler-down scheduler-ps scheduler-logs

help:
	@echo "Targets:"
	@echo "  make check-env      - verify .env exists"
	@echo "  make network        - create shared overlay network if missing"
	@echo "  make validate       - validate ES stack files"
	@echo "=== ES ==="
	@echo "  make es-bootstrap   - deploy ES bootstrap stack"
	@echo "  make es-up          - deploy normal ES stack"
	@echo ""
	@echo "=== LEGACY ==="
	@echo "  make bootstrap      - (alias for es-bootstrap)"
	@echo "  make up             - (alias for es-up)"
	@echo "  make wait           - wait for ES API to respond"
	@echo "  make health         - show cluster health"
	@echo "  make nodes          - show node list"
	@echo "  make shards         - show shard allocation"
	@echo "  make ps             - show swarm tasks for the ES stack"
	@echo "  make logs           - tail logs for es01"
	@echo "  make logs-es02      - tail logs for es02"
	@echo "  make logs-es03      - tail logs for es03"
	@echo "  make down           - remove the ES stack"
	@echo "  make clean-history  - remove ES stack and bring it back with normal stack"
	@echo "  make es-build       - build Vault-enabled Elasticsearch image"
	@echo "  make vault-vars     - pull and print variables from Vault"
	@echo "  make mgmt-build     - build one-shot MGMT setup image"
	@echo "  make es-setup       - run one-shot ES post-bootstrap setup"
	@echo "  make kibana-build   - build Vault-enabled Kibana image"
	@echo "  make kibana-up      - deploy Kibana stack"
	@echo "  make kibana-down    - remove Kibana stack"
	@echo "  make kibana-ps      - show Kibana stack status"
	@echo "  make kibana-logs    - tail Kibana logs"
	@echo "  make logstash-build - build Vault-enabled Logstash image"
	@echo "  make logstash-up    - deploy Logstash stack"
	@echo "  make logstash-down  - remove Logstash stack"
	@echo "  make logstash-ps    - show Logstash stack status"
	@echo "  make logstash-logs  - tail Logstash logs"
	@echo "  make scheduler-build - build Vault-enabled Scheduler image"
	@echo "  make scheduler-up    - deploy Scheduler stack"
	@echo "  make scheduler-down  - remove Scheduler stack"
	@echo "  make scheduler-ps    - show Scheduler stack status"
	@echo "  make scheduler-logs  - tail Scheduler logs"

check-env:
	@if [[ ! -f "$(ENV_FILE)" ]]; then
		echo "Missing $(ENV_FILE)"
		exit 1
	fi
	@echo "Using $(ENV_FILE)"

network: check-env
	@if ! docker network inspect $(NETWORK_NAME) >/dev/null 2>&1; then
		docker network create --driver overlay --attachable $(NETWORK_NAME)
		echo "Created network $(NETWORK_NAME)"
	else
		echo "Network $(NETWORK_NAME) already exists"
	fi

validate: check-env
	docker compose --env-file $(ENV_FILE) -f $(ES_BOOTSTRAP_STACK) config >/dev/null
	docker compose --env-file $(ENV_FILE) -f $(ES_STACK) config >/devS/null
	@echo "ES stack files validate cleanly"

es-bootstrap: check-env network validate es-build
	set -a
	source $(ENV_FILE)
	set +a
	docker stack deploy -c $(ES_BOOTSTRAP_STACK) $(STACK_NAME)

es-up: check-env network validate es-build
	set -a
	source $(ENV_FILE)
	set +a
	docker stack deploy -c $(ES_STACK) $(STACK_NAME)

wait: check-env
	set -a
	source $(ENV_FILE)
	set +a
	@if [[ -z "$$VAULT_ADDR" || -z "$$VAULT_TOKEN" || -z "$$VAULT_SECRET_PATH" ]]; then
		echo "Missing VAULT_ADDR, VAULT_TOKEN, or VAULT_SECRET_PATH in $(ENV_FILE)"
		exit 1
	fi
	ELASTIC_PASSWORD="$$(curl -s \
	  -H "X-Vault-Token: $$VAULT_TOKEN" \
	  "$$VAULT_ADDR/v1/$$VAULT_SECRET_PATH" | $(VAULT_GET_PY))"
	echo "Waiting for Elasticsearch on $(ES_URL) ..."
	until curl -k -s -u elastic:$$ELASTIC_PASSWORD $(ES_URL) >/dev/null 2>&1; do
		sleep 5
	done
	echo "Elasticsearch is responding"

health: check-env
	set -a
	source $(ENV_FILE)
	set +a
	ELASTIC_PASSWORD="$$(curl -s \
	  -H "X-Vault-Token: $$VAULT_TOKEN" \
	  "$$VAULT_ADDR/v1/$$VAULT_SECRET_PATH" | $(VAULT_GET_PY))"
	curl -k -u elastic:$$ELASTIC_PASSWORD $(ES_URL)/_cluster/health?pretty

nodes: check-env
	set -a
	source $(ENV_FILE)
	set +a
	ELASTIC_PASSWORD="$$(curl -s \
	  -H "X-Vault-Token: $$VAULT_TOKEN" \
	  "$$VAULT_ADDR/v1/$$VAULT_SECRET_PATH" | $(VAULT_GET_PY))"
	curl -k -u elastic:$$ELASTIC_PASSWORD $(ES_URL)/_cat/nodes?v

shards: check-env
	set -a
	source $(ENV_FILE)
	set +a
	ELASTIC_PASSWORD="$$(curl -s \
	  -H "X-Vault-Token: $$VAULT_TOKEN" \
	  "$$VAULT_ADDR/v1/$$VAULT_SECRET_PATH" | $(VAULT_GET_PY))"
	curl -k -u elastic:$$ELASTIC_PASSWORD $(ES_URL)/_cat/shards?v

ps:
	docker stack services $(STACK_NAME) || true
	echo
	docker stack ps $(STACK_NAME) || true

logs:
	docker service logs $(STACK_NAME)_es01 --tail 100 -f

logs-es02:
	docker service logs $(STACK_NAME)_es02 --tail 100 -f

logs-es03:
	docker service logs $(STACK_NAME)_es03 --tail 100 -f

down:
	docker stack rm $(STACK_NAME)

clean-history: down
	sleep 10
	$(MAKE) es-up

vault-vars: check-env
	set -a
	source $(ENV_FILE)
	set +a
	@if [[ -z "$$VAULT_ADDR" ]]; then
		echo "Missing VAULT_ADDR in $(ENV_FILE)"
		exit 1
	fi
	@if [[ -z "$$VAULT_TOKEN" ]]; then
		echo "Missing VAULT_TOKEN in $(ENV_FILE)"
		exit 1
	fi
	@if [[ -z "$$VAULT_SECRET_PATH" ]]; then
		echo "Missing VAULT_SECRET_PATH in $(ENV_FILE)"
		exit 1
	fi
	python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["data"]["data"], indent=2))' < <(curl -s \
	  -H "X-Vault-Token: $$VAULT_TOKEN" \
	  "$$VAULT_ADDR/v1/$$VAULT_SECRET_PATH")


es-build: check-env
	set -a
	source $(ENV_FILE)
	set +a
	@if [[ -z "$$STACK_VERSION" ]]; then
		echo "Missing STACK_VERSION in $(ENV_FILE)"
		exit 1
	fi
	docker build \
	  --build-arg STACK_VERSION=$$STACK_VERSION \
	  -t esiem/elasticsearch-vault:$$STACK_VERSION \
	  -f ES/Dockerfile .

# Backward compatibility
bootstrap: es-bootstrap
up: es-up

mgmt-build: check-env
	set -a
	source $(ENV_FILE)
	set +a
	docker build \
	  --build-arg PYTHON_ELASTICSEARCH_VERSION=$$PYTHON_ELASTICSEARCH_VERSION \
	  -t $(MGMT_IMAGE_NAME):latest \
	  -f MGMT-Setup/Dockerfile MGMT-Setup

es-setup: check-env mgmt-build
	set -a
	source $(ENV_FILE)
	set +a
	@if [[ -z "$$VAULT_ADDR" || -z "$$VAULT_TOKEN" || -z "$$VAULT_SECRET_PATH" ]]; then
		echo "Missing VAULT_ADDR, VAULT_TOKEN, or VAULT_SECRET_PATH in $(ENV_FILE)"
		exit 1
	fi
	docker run --rm \
	  --network $(NETWORK_NAME) \
	  -e VAULT_ADDR=$$VAULT_ADDR \
	  -e VAULT_TOKEN=$$VAULT_TOKEN \
	  -e VAULT_SECRET_PATH=$$VAULT_SECRET_PATH \
	  $(MGMT_IMAGE_NAME):latest


kibana-build: check-env
	set -a
	source $(ENV_FILE)
	set +a
	@if [[ -z "$$STACK_VERSION" ]]; then
		echo "Missing STACK_VERSION in $(ENV_FILE)"
		exit 1
	fi
	docker build \
	  --build-arg STACK_VERSION=$$STACK_VERSION \
	  -t $(KIBANA_IMAGE_NAME):$$STACK_VERSION \
	  -f Kibana/Dockerfile .

kibana-up: check-env network kibana-build
	set -a
	source $(ENV_FILE)
	set +a
	docker stack deploy -c $(KIBANA_STACK) $(KIBANA_STACK_NAME)

kibana-down:
	docker stack rm $(KIBANA_STACK_NAME)

kibana-ps:
	docker stack services $(KIBANA_STACK_NAME) || true
	echo
	docker stack ps $(KIBANA_STACK_NAME) || true

kibana-logs:
	docker service logs $(KIBANA_STACK_NAME)_kibana --tail 100 -f

logstash-build: check-env
	set -a
	source $(ENV_FILE)
	set +a
	@if [[ -z "$$STACK_VERSION" ]]; then
		echo "Missing STACK_VERSION in $(ENV_FILE)"
		exit 1
	fi
	docker build \
	  --build-arg STACK_VERSION=$$STACK_VERSION \
	  -t $(LOGSTASH_IMAGE_NAME):$$STACK_VERSION \
	  -f Logstash/Dockerfile .

logstash-up: check-env network logstash-build
	set -a
	source $(ENV_FILE)
	set +a
	docker stack deploy -c $(LOGSTASH_STACK) $(LOGSTASH_STACK_NAME)

logstash-down:
	docker stack rm $(LOGSTASH_STACK_NAME)

logstash-ps:
	docker stack services $(LOGSTASH_STACK_NAME) || true
	echo
	docker stack ps $(LOGSTASH_STACK_NAME) || true

logstash-logs:
	docker service logs $(LOGSTASH_STACK_NAME)_logstash --tail 100 -f

scheduler-build: check-env
	set -a
	source $(ENV_FILE)
	set +a
	docker build \
	  -t $(SCHEDULER_IMAGE_NAME):$$STACK_VERSION \
	  -f Scheduler/Dockerfile Scheduler

scheduler-up: check-env network scheduler-build
	set -a
	source $(ENV_FILE)
	set +a
	docker stack deploy -c $(SCHEDULER_STACK) $(SCHEDULER_STACK_NAME)

scheduler-down:
	docker stack rm $(SCHEDULER_STACK_NAME)

scheduler-ps:
	docker stack services $(SCHEDULER_STACK_NAME) || true
	echo
	docker stack ps $(SCHEDULER_STACK_NAME) || true

scheduler-logs:
	docker service logs $(SCHEDULER_STACK_NAME)_scheduler --tail 100 -f