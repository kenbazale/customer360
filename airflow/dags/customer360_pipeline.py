"""
customer360_pipeline.py
Daily orchestration of the Customer 360 pipeline:

    1. dlt ingestion           - land raw extracts to S3
    2. GX validation           - pre-load quality gate, produces Data Docs report
    3. dbt run                 - staging -> intermediate -> mart in Snowflake
    4. dbt test                - enforce mart-level data quality (error severity)
    5. pipeline health summary - query the mart post-run, log a health snapshot

Observability: every task reports failures to alerts.alert_on_failure
(structured JSON log + optional Slack webhook), and the two longest-running
tasks (dbt_run, dbt_test) have SLAs configured so a silently slow run gets
flagged rather than just eventually finishing.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

from alerts import alert_on_failure, alert_on_sla_miss

default_args = {
    "owner": "ken_bazale",
    "retries": 1,
    "on_failure_callback": alert_on_failure,
}

with DAG(
    dag_id="customer360_pipeline",
    description="Ingest, validate, transform, test, and monitor the Customer 360 banking dataset",
    default_args=default_args,
    schedule="@daily",
    start_date=datetime(2026, 8, 1),
    catchup=False,
    sla_miss_callback=alert_on_sla_miss,
    tags=["customer360", "banking", "portfolio"],
) as dag:

    dlt_ingestion = BashOperator(
        task_id="dlt_ingestion",
        bash_command="cd /opt/project/ingestion && python3 pipeline.py",
        # Set S3 connection timeouts to fail faster on connectivity issues
        # Default is usually 60s, reducing to 30s for quicker detection
        env={
            "AWS_CONNECT_TIMEOUT": "10",
            "AWS_READ_TIMEOUT": "30",
            "BOTOCORE_CONNECT_TIMEOUT": "10",
            "BOTOCORE_READ_TIMEOUT": "30",
        },
    )

    gx_validation = BashOperator(
        task_id="gx_validation",
        bash_command="cd /opt/project/quality && python3 run_validation.py",
        retries=0,
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command="cd /opt/project/dbt && dbt run --select staging intermediate customer_360",
        sla=timedelta(minutes=10),
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command="cd /opt/project/dbt && dbt test --select customer_360",
        sla=timedelta(minutes=5),
    )

    pipeline_health_summary = BashOperator(
        task_id="pipeline_health_summary",
        bash_command="cd /opt/project/quality && python3 pipeline_health_summary.py",
    )

    dlt_ingestion >> gx_validation >> dbt_run >> dbt_test >> pipeline_health_summary