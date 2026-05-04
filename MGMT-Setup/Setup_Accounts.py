import time
import os
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError


CLIENT_DOMAIN = os.getenv("CLIENT_DOMAIN")
ELASTIC_PASSWORD = os.getenv("ELASTIC_PASSWORD", "")
KIBANA_PASSWORD = os.getenv("KIBANA_PASSWORD", "")
ELASTIC_HOST = os.getenv("ELASTIC_HOST", f"https://es01.{CLIENT_DOMAIN}:9200")
ELASTIC_USER = os.getenv("ELASTIC_USER", "elastic")


def initialize_es_client(elastic_server, username, password):
    try:
        return Elasticsearch(
            elastic_server,
            http_auth=(username, password),
            verify_certs=True,
            request_timeout=30,
        )
    except Exception as error:
        print("Elasticsearch Client Error:", error)
        raise SystemExit(1)


es = initialize_es_client(ELASTIC_HOST, ELASTIC_USER, ELASTIC_PASSWORD)


while True:
    try:
        health = es.cluster.health()
        if health.get("status") in ["yellow", "green"]:
            print(f"Cluster is ready: {health.get('status')}")
            break

        print(f"Cluster not ready yet: {health.get('status')}")
        time.sleep(10)

    except Exception as error:
        print(f"Waiting for Elasticsearch cluster: {error}")
        time.sleep(10)


while True:
    try:
        response = es.security.change_password(
            username="kibana_system",
            body={"password": KIBANA_PASSWORD},
        )

        print(f"response: {response}")
        print("Password changed successfully for kibana_system.")

        with open("/setup_completed.flag", "w") as flag_file:
            flag_file.write("")

        break

    except ConnectionError as error:
        print(f"Connection error: {error}, retrying in 10 seconds.")
        time.sleep(10)

    except Exception as error:
        print(f"Password change failed: {error}, retrying in 10 seconds.")
        time.sleep(10)