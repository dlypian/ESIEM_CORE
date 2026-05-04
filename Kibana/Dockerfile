ARG STACK_VERSION
FROM docker.elastic.co/kibana/kibana:${STACK_VERSION}

USER root

RUN set -eux; \
    apt-get update -o Acquire::Retries=5; \
    apt-get install -y --no-install-recommends curl jq ca-certificates; \
    rm -rf /var/lib/apt/lists/*

COPY Kibana/vault-entrypoint.sh /usr/local/bin/vault-entrypoint.sh
RUN chmod +x /usr/local/bin/vault-entrypoint.sh

USER kibana

ENTRYPOINT ["/usr/local/bin/vault-entrypoint.sh"]