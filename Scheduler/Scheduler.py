from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import (
    EVENT_JOB_EXECUTED,
    EVENT_JOB_ERROR,
    EVENT_JOB_MISSED,
    EVENT_JOB_MAX_INSTANCES,
)

import time
import json
import subprocess
import os
import sys
import signal
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone

from elasticsearch import Elasticsearch
from VaultSecrets import get_vault_secrets


# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------

LOG_FILE = os.getenv("SCHEDULER_LOG_FILE", "Scheduler.log")
LOG_LEVEL = os.getenv("SCHEDULER_LOG_LEVEL", "INFO").upper()

logger = logging.getLogger("swarm.scheduler")
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
logger.handlers.clear()
logger.propagate = False

formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=10 * 1024 * 1024,
    backupCount=3,
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


def clean_error(error):
    return str(error).replace("\r", " ").replace("\n", " ").strip()


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def safe_json(data):
    try:
        return json.dumps(data, sort_keys=True, default=str)
    except Exception:
        return str(data)


# ----------------------------------------------------------------------
# Vault / Elasticsearch
# ----------------------------------------------------------------------

def get_es_config():
    logger.debug("Loading Elasticsearch config from Vault")

    secrets = get_vault_secrets()

    client_domain = secrets.get("CLIENT_DOMAIN")
    elastic_host = secrets.get("ELASTIC_HOST") or (
        f"https://es01.{client_domain}:9200" if client_domain else None
    )
    elastic_user = secrets.get("ELASTIC_USER", "elastic")
    elastic_password = secrets.get("ELASTIC_PASSWORD")

    if not elastic_host:
        raise RuntimeError("ELASTIC_HOST missing from Vault and CLIENT_DOMAIN is unavailable")

    if not elastic_user:
        raise RuntimeError("ELASTIC_USER missing from Vault")

    if not elastic_password:
        raise RuntimeError("ELASTIC_PASSWORD missing from Vault")

    logger.debug("Loaded Elasticsearch config host=%s user=%s", elastic_host, elastic_user)

    return elastic_host, elastic_user, elastic_password


def initialize_es_client(elastic_server, elastic_username, elastic_password):
    if not elastic_server:
        logger.error("ELASTICSEARCH_CONNECT_FAILED reason=missing_host")
        return None

    try:
        logger.info("ELASTICSEARCH_CONNECT_START host=%s", elastic_server)

        es_client = Elasticsearch(
            elastic_server,
            basic_auth=(elastic_username, elastic_password),
            verify_certs=True,
            request_timeout=30,
        )

        if not es_client.ping():
            raise ValueError("Elasticsearch connection failed: server not responding")

        logger.info("ELASTICSEARCH_CONNECT_OK host=%s", elastic_server)
        return es_client

    except Exception as error:
        logger.exception(
            "ELASTICSEARCH_CONNECT_FAILED host=%s error_type=%s error=%s",
            elastic_server,
            type(error).__name__,
            clean_error(error),
        )
        return None


# ----------------------------------------------------------------------
# Scheduler setup
# ----------------------------------------------------------------------

scheduler_timezone = os.getenv("TZ", "UTC")
scheduler = BackgroundScheduler(timezone=scheduler_timezone)
scheduled_task_signatures = {}
es = None


def scheduler_heartbeat():
    logger.info("SCHEDULER_HEARTBEAT status=alive timezone=%s utc=%s", scheduler_timezone, utc_now())


def scheduler_event_listener(event):
    job_id = getattr(event, "job_id", "unknown")

    if event.code == EVENT_JOB_EXECUTED:
        logger.info("SCHEDULER_JOB_EXECUTED job_id=%s", job_id)

    elif event.code == EVENT_JOB_ERROR:
        exception = getattr(event, "exception", None)
        logger.error(
            "SCHEDULER_JOB_ERROR job_id=%s error_type=%s error=%s",
            job_id,
            type(exception).__name__ if exception else "None",
            clean_error(exception) if exception else "",
        )

    elif event.code == EVENT_JOB_MISSED:
        logger.warning("SCHEDULER_JOB_MISSED job_id=%s", job_id)

    elif event.code == EVENT_JOB_MAX_INSTANCES:
        logger.warning("SCHEDULER_JOB_MAX_INSTANCES job_id=%s", job_id)


scheduler.add_listener(
    scheduler_event_listener,
    EVENT_JOB_EXECUTED
    | EVENT_JOB_ERROR
    | EVENT_JOB_MISSED
    | EVENT_JOB_MAX_INSTANCES,
)


def add_heartbeat_job():
    scheduler.add_job(
        scheduler_heartbeat,
        "interval",
        seconds=60,
        id="scheduler_heartbeat",
        name="scheduler_heartbeat",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )


# ----------------------------------------------------------------------
# Task loading
# ----------------------------------------------------------------------

def fetch_tasks_from_elasticsearch():
    global es

    logger.info("TASK_FETCH_START index=tasks")

    if es is None:
        logger.warning("TASK_FETCH_RETRY reason=elasticsearch_client_not_initialized")

        try:
            elastic_host, elastic_user, elastic_password = get_es_config()
            es = initialize_es_client(elastic_host, elastic_user, elastic_password)
        except Exception as error:
            logger.exception(
                "TASK_FETCH_CONFIG_FAILED error_type=%s error=%s",
                type(error).__name__,
                clean_error(error),
            )
            return []

    if es is None:
        logger.error("TASK_FETCH_FAILED reason=elasticsearch_unavailable")
        return []

    try:
        response = es.search(
            index="tasks",
            query={"match_all": {}},
            size=10000,
        )

        current_jobs = [hit["_source"] for hit in response["hits"]["hits"]]

        logger.info("TASK_FETCH_OK count=%d index=tasks", len(current_jobs))
        return current_jobs

    except Exception as error:
        logger.exception(
            "TASK_FETCH_FAILED index=tasks error_type=%s error=%s",
            type(error).__name__,
            clean_error(error),
        )
        return []


# ----------------------------------------------------------------------
# Script execution
# ----------------------------------------------------------------------

def run_script(**job_config):
    task = dict(job_config)

    script_name = task.pop("script", "")
    vault_env = task.pop("vault_env", {})
    task_name = task.get("name", script_name or "<no name>")

    if not script_name:
        logger.error("JOB_FAILED task=%s reason=missing_script", task_name)
        return

    start = datetime.now(timezone.utc)

    logger.info(
        "JOB_START task=%s script=%s utc=%s param_keys=%s vault_env_keys=%s",
        task_name,
        script_name,
        utc_now(),
        sorted(task.keys()),
        sorted(vault_env.keys()),
    )

    try:
        secrets = get_vault_secrets()
        child_env = os.environ.copy()
        missing_secrets = []

        for env_var_name, vault_secret_name in vault_env.items():
            secret_value = secrets.get(vault_secret_name)

            if not secret_value:
                missing_secrets.append(vault_secret_name)
                continue

            child_env[env_var_name] = str(secret_value)

        if missing_secrets:
            elapsed = (datetime.now(timezone.utc) - start).total_seconds()

            logger.error(
                "JOB_FAILED task=%s script=%s reason=missing_vault_secrets missing=%s elapsed_seconds=%.1f",
                task_name,
                script_name,
                ",".join(missing_secrets),
                elapsed,
            )
            return

        kwargs_json = json.dumps(task, default=str)

        result = subprocess.run(
            [sys.executable, script_name, kwargs_json],
            check=False,
            env=child_env,
        )

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()

        if result.returncode == 0:
            logger.info(
                "JOB_END task=%s script=%s returncode=%s elapsed_seconds=%.1f",
                task_name,
                script_name,
                result.returncode,
                elapsed,
            )
        else:
            logger.error(
                "JOB_FAILED task=%s script=%s returncode=%s elapsed_seconds=%.1f",
                task_name,
                script_name,
                result.returncode,
                elapsed,
            )

    except Exception as error:
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()

        logger.exception(
            "JOB_FAILED task=%s script=%s elapsed_seconds=%.1f error_type=%s error=%s",
            task_name,
            script_name,
            elapsed,
            type(error).__name__,
            clean_error(error),
        )


# ----------------------------------------------------------------------
# Scheduling
# ----------------------------------------------------------------------

def task_signature(task):
    return json.dumps(task, sort_keys=True, default=str)


def schedule_tasks(task_config):
    global scheduled_task_signatures

    logger.info("TASK_RECONCILE_START desired_count=%d", len(task_config))

    desired_job_ids = set()

    for task in task_config:
        task_name = task.get("name", "<no name>")
        script_name = task.get("script", "")
        cron_expression = str(task.get("schedule", "")).strip()

        job_id = f"task:{task_name}"
        desired_job_ids.add(job_id)

        if not script_name:
            logger.warning("TASK_SKIPPED name=%s reason=missing_script", task_name)
            continue

        if not cron_expression:
            logger.warning("TASK_SKIPPED name=%s script=%s reason=missing_schedule", task_name, script_name)
            continue

        signature = task_signature(task)
        existing_job = scheduler.get_job(job_id)
        existing_signature = scheduled_task_signatures.get(job_id)

        if existing_job and existing_signature == signature:
            logger.debug("TASK_UNCHANGED name=%s job_id=%s", task_name, job_id)
            continue

        if existing_job:
            logger.info("TASK_UPDATED name=%s job_id=%s", task_name, job_id)
            scheduler.remove_job(job_id)

        try:
            scheduler.add_job(
                run_script,
                trigger=CronTrigger.from_crontab(cron_expression),
                kwargs=task,
                id=job_id,
                name=task_name,
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=300,
            )

            scheduled_task_signatures[job_id] = signature
            job = scheduler.get_job(job_id)

            logger.info(
                "TASK_SCHEDULED name=%s script=%s cron=%r job_id=%s next_run_time=%s",
                task_name,
                script_name,
                cron_expression,
                job_id,
                job.next_run_time if job else None,
            )

        except Exception as error:
            logger.exception(
                "TASK_SCHEDULE_FAILED name=%s script=%s cron=%r error_type=%s error=%s",
                task_name,
                script_name,
                cron_expression,
                type(error).__name__,
                clean_error(error),
            )

    for job in scheduler.get_jobs():
        if job.id == "scheduler_heartbeat":
            continue

        if job.id.startswith("task:") and job.id not in desired_job_ids:
            logger.info("TASK_REMOVED_STALE job_id=%s name=%s", job.id, job.name)
            scheduler.remove_job(job.id)
            scheduled_task_signatures.pop(job.id, None)

    logger.info("TASK_RECONCILE_END active_count=%d", len(scheduler.get_jobs()))


def log_active_jobs():
    jobs = scheduler.get_jobs()

    logger.info("ACTIVE_JOBS count=%d", len(jobs))

    for job in jobs:
        logger.info(
            "ACTIVE_JOB id=%s name=%s next_run_time=%s",
            job.id,
            job.name,
            job.next_run_time,
        )


# ----------------------------------------------------------------------
# Shutdown handling
# ----------------------------------------------------------------------

def handle_shutdown(signum, frame):
    logger.warning("SCHEDULER_SHUTDOWN signal=%s utc=%s", signum, utc_now())

    try:
        scheduler.shutdown(wait=False)
    except Exception as error:
        logger.exception(
            "SCHEDULER_SHUTDOWN_ERROR error_type=%s error=%s",
            type(error).__name__,
            clean_error(error),
        )

    sys.exit(0)


signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main():
    logger.info(
        "SCHEDULER_START status=starting timezone=%s log_file=%s log_level=%s utc=%s",
        scheduler_timezone,
        LOG_FILE,
        LOG_LEVEL,
        utc_now(),
    )

    add_heartbeat_job()
    scheduler.start()

    logger.info("SCHEDULER_START status=started utc=%s", utc_now())

    while True:
        try:
            task_config = fetch_tasks_from_elasticsearch()

            logger.info("TASK_CONFIG count=%d", len(task_config))
            logger.debug("TASK_CONFIG_DETAIL data=%s", safe_json(task_config))

            schedule_tasks(task_config)
            log_active_jobs()

        except Exception as error:
            logger.exception(
                "SCHEDULER_LOOP_ERROR error_type=%s error=%s",
                type(error).__name__,
                clean_error(error),
            )

        time.sleep(60)


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        logger.warning("SCHEDULER_SHUTDOWN reason=KeyboardInterrupt utc=%s", utc_now())

        try:
            scheduler.shutdown(wait=False)
        except Exception as error:
            logger.exception(
                "SCHEDULER_SHUTDOWN_ERROR error_type=%s error=%s",
                type(error).__name__,
                clean_error(error),
            )

    except Exception as error:
        logger.exception(
            "SCHEDULER_CRASH error_type=%s error=%s",
            type(error).__name__,
            clean_error(error),
        )
        raise