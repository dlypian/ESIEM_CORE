from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import time
import json
import subprocess
import os
from elasticsearch import Elasticsearch
import logging
from logging.handlers import RotatingFileHandler
from VaultSecrets import get_vault_secrets

# Set up a specific logger
logger = logging.getLogger('MyLogger')
logger.setLevel(logging.DEBUG)

# Add the log message handler to the logger
handler = RotatingFileHandler('Scheduler.log', maxBytes=10*1024*1024, backupCount=1)  # 10 MB

# Create a formatter that includes a timestamp
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Add the handler to the logger <-- This is the line you need to add
logger.addHandler(handler)


def get_es_config():
    secrets = get_vault_secrets()

    client_domain = secrets.get("CLIENT_DOMAIN")
    elastic_host = secrets.get("ELASTIC_HOST") or f"https://es01.{client_domain}:9200"
    elastic_user = secrets.get("ELASTIC_USER", "elastic")
    elastic_password = secrets.get("ELASTIC_PASSWORD")

    if not elastic_host:
        raise RuntimeError("ELASTIC_HOST missing from Vault")

    if not elastic_user:
        raise RuntimeError("ELASTIC_USER missing from Vault")

    if not elastic_password:
        raise RuntimeError("ELASTIC_PASSWORD missing from Vault")

    return elastic_host, elastic_user, elastic_password


def initialize_es_client(elasticServer, ELASTIC_USERNAME, ELASTIC_PASSWORD):
    try:
        logger.debug("Connecting to Elasticsearch at %s", elasticServer)
        
        es = Elasticsearch(
            elasticServer,
            basic_auth=(ELASTIC_USERNAME, ELASTIC_PASSWORD),  
            verify_certs=True,
            request_timeout=30                               
        )

        if not es.ping():
            raise ValueError("Elasticsearch connection failed: Server not responding")

        logger.debug("Successfully connected to Elasticsearch")
        return es

    except Exception as error:
        logger.exception("Elasticsearch Client Error: %s", error)
        return None


# Function to update and schedule jobs
def update_and_schedule_jobs():
    global es

    logger.info("Running update_and_schedule_jobs")

    if es is None:
        logger.error("Elasticsearch client is not initialized")
        return []

    for job in scheduler.get_jobs():
        scheduler.remove_job(job.id)

    logger.info("Cleared existing jobs")

    try:
        response = es.search(
            index="tasks",
            query={"match_all": {}},
            size=10000
        )
        current_jobs = [hit["_source"] for hit in response["hits"]["hits"]]
        print(f"Fetched {len(current_jobs)} jobs from Elasticsearch")

    except Exception as error:
        logger.exception("Error reading tasks from Elasticsearch: %s", error)
        current_jobs = []

    print("Updating and scheduling tasks:")
    return current_jobs


def run_script(**kwargs):
    script_name = kwargs.get('script', '')
    # Remove 'script' from kwargs to pass the rest as JSON
    kwargs.pop('script', None)
    # Convert the remaining kwargs to JSON
    kwargs_json = json.dumps(kwargs)
    
    try:
        logger.info("Running script: %s with kwargs: %s", script_name, kwargs)
        # Pass the JSON string as a single command-line argument after encoding it to handle special characters
        subprocess.run(['python', script_name, kwargs_json], check=True)
    except subprocess.CalledProcessError as e:
        logger.exception("Error running script %s: %s", script_name, e)
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
    logger.info("Completed script: %s", script_name)



def schedule_tasks(scheduler, task_config):
    scheduler.remove_all_jobs()

    for task in task_config:
        task_name = task.get("name", "<no name>")
        cron_expression = str(task.get("schedule", "")).strip()

        if not cron_expression:
            logger.warning("Task %s has no schedule", task_name)
            continue

        try:
            scheduler.add_job(
                run_script,
                CronTrigger.from_crontab(cron_expression),
                kwargs=task,
                id=task_name,
                replace_existing=True
            )
            logger.info("Scheduled task %s with %r", task_name, cron_expression)

        except Exception:
            logger.exception("Invalid cron for task %s: %r", task_name, cron_expression)
            continue

# Initialize Elasticsearch clienth 
es = None

# Create a background scheduler
scheduler_timezone = os.getenv("TZ", "UTC")
scheduler = BackgroundScheduler(timezone=scheduler_timezone)

# Start the scheduler
scheduler.start()

try:
    while True:
        elastic_host, elastic_user, elastic_password = get_es_config()
        es = initialize_es_client(elastic_host, elastic_user, elastic_password)

        task_config = update_and_schedule_jobs()
        logger.info("Current Jobs:\n%s", json.dumps(task_config, indent=2))

        schedule_tasks(scheduler, task_config)
        time.sleep(59)  # Sleep for 59 seconds
except KeyboardInterrupt:
    scheduler.shutdown()
