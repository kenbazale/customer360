"""
alerts.py
Shared observability callbacks for the customer360_pipeline DAG.

Design intent: a real ops team wants to know the moment a pipeline task
fails or runs abnormally long, without having to be staring at the Airflow
UI. This module writes structured, machine-parseable alert records to a
local log file (so there's always a durable record, viewable without any
external service), and optionally forwards the same alert to Slack if a
webhook URL is configured via environment variable - the same pattern a
production setup would use, just with the notification channel left as an
opt-in rather than a hard dependency.

No external service is required to demonstrate this - the JSON log file
alone is the artifact worth showing in an interview: "here's how the
pipeline tells you something broke."
"""

import json
import os
from datetime import datetime, timezone

ALERT_LOG_PATH = "/opt/airflow/logs/pipeline_alerts.jsonl"
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")


def _write_alert_record(record: dict) -> None:
    os.makedirs(os.path.dirname(ALERT_LOG_PATH), exist_ok=True)
    with open(ALERT_LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


def _send_slack_notification(text: str) -> None:
    if not SLACK_WEBHOOK_URL:
        return
    try:
        import requests

        requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=5)
    except Exception as e:
        # Never let a notification failure break the DAG's own error
        # handling - log it and move on.
        print(f"[alerts] Slack notification failed: {e}")


def alert_on_failure(context) -> None:
    """on_failure_callback - fires when any task in the DAG fails."""
    task_instance = context.get("task_instance")
    dag_run = context.get("dag_run")

    record = {
        "event": "task_failure",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dag_id": task_instance.dag_id if task_instance else None,
        "task_id": task_instance.task_id if task_instance else None,
        "run_id": dag_run.run_id if dag_run else None,
        "try_number": task_instance.try_number if task_instance else None,
        "log_url": task_instance.log_url if task_instance else None,
    }

    _write_alert_record(record)

    _send_slack_notification(
        f":red_circle: *customer360_pipeline* task failed: "
        f"`{record['task_id']}` (run: {record['run_id']})\n"
        f"Logs: {record['log_url']}"
    )


def alert_on_sla_miss(dag, task_list, blocking_task_list, slas, blocking_tis) -> None:
    """sla_miss_callback - fires when a task exceeds its expected runtime."""
    record = {
        "event": "sla_miss",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dag_id": dag.dag_id,
        "tasks_affected": [sla.task_id for sla in slas],
    }

    _write_alert_record(record)

    _send_slack_notification(
        f":warning: *customer360_pipeline* SLA missed for tasks: "
        f"{', '.join(record['tasks_affected'])}"
    )