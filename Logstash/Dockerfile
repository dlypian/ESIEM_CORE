ARG STACK_VERSION
FROM docker.elastic.co/logstash/logstash:${STACK_VERSION}

USER root

RUN mkdir -p /usr/share/logstash/config/certs

COPY Logstash/vault-entrypoint.sh /usr/local/bin/vault-entrypoint.sh
RUN chmod +x /usr/local/bin/vault-entrypoint.sh

USER logstash

ENTRYPOINT ["/usr/local/bin/vault-entrypoint.sh"]