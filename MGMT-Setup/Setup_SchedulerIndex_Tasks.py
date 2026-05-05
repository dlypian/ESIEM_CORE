from elasticsearch import Elasticsearch
import os
from datetime import datetime


now = datetime.now()
print("now:", now)

CLIENT_DOMAIN = os.getenv("CLIENT_DOMAIN")
ELASTIC_HOST = os.getenv("ELASTIC_HOST", f"https://es01.{CLIENT_DOMAIN}:9200")
ELASTIC_USER = os.getenv("ELASTIC_USER", "elastic")
ELASTIC_PASSWORD = os.getenv("ELASTIC_PASSWORD")


settings = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
    },
    "mappings": {
        "properties": {
            "name": {"type": "text"},
            "schedule": {"type": "text"},
            "script": {"type": "text"},
            "notify": {"type": "keyword"},
        }
    },
}

data = [
    {
        "name": "VaultSync",
        "script": "VaultSync.py",
        "schedule": "* * * * *",
        "notify": ["daniel.lypian@esiem.io"],
    }
]


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

index = "tasks"

if not es.indices.exists(index=index):
    es.indices.create(index=index, body=settings)
    print(f"Created index '{index}'")
else:
    print(f"Index '{index}' already exists")

for task in data:
    res = es.index(index=index, id=task["name"], document=task)
    print(f"Task {task['name']}: {res['result']}")