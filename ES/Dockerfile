ARG STACK_VERSION
FROM docker.elastic.co/elasticsearch/elasticsearch:${STACK_VERSION}

USER root

RUN microdnf install -y curl jq || yum install -y curl jq

COPY ES/vault-entrypoint.sh /usr/local/bin/vault-entrypoint.sh
RUN chmod +x /usr/local/bin/vault-entrypoint.sh

USER elasticsearch

ENTRYPOINT ["/usr/local/bin/vault-entrypoint.sh"]