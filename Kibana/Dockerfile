ARG STACK_VERSION
FROM docker.elastic.co/kibana/kibana:${STACK_VERSION}

USER root

COPY Kibana/vault-entrypoint.sh /usr/local/bin/vault-entrypoint.sh
RUN chmod +x /usr/local/bin/vault-entrypoint.sh

USER kibana

ENTRYPOINT ["/usr/local/bin/vault-entrypoint.sh"]