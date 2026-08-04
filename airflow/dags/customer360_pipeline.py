"""
customer360_pipeline.py
Daily orchestration of the Customer 360 pipeline:

    1. dlt ingestion   - land raw extracts to S3
    2. GX validation   - pre-load quality gate, produces Data Docs report
    3. dbt run         - staging -> intermediate -> mart in Snowflake
    4. dbt test        - enforce mart-level data quality (error severity)

Each task shells out to the actual project scripts (mounted into the
container via docker-compose.yaml), rather than reimplementing pipeline
logic inside the DAG. Airflow's job here is scheduling and dependency
ordering, not the transformation logic itself - that all still lives in
the dlt/GX/dbt projects, exactly as it would in a real production setup.
"""

from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "ken_bazale",
    "retries": 1,
}

with DAG(
    dag_id="customer360_pipeline",
    description="Ingest, validate, transform, and test the Customer 360 banking dataset",
    default_args=default_args,
    schedule="@daily",
    start_date=datetime(2026, 8, 1),
    catchup=False,
    tags=["customer360", "banking", "portfolio"],
) as dag:

    dlt_ingestion = BashOperator(
        task_id="dlt_ingestion",
        bash_command="cd /opt/project/ingestion && python3 pipeline.py",
    )

    gx_validation = BashOperator(
        task_id="gx_validation",
        bash_command="cd /opt/project/quality && python3 run_validation.py",
        retries=0,
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            "cd /opt/project/dbt && "
            "dbt run --target-path /tmp/dbt_target --log-path /tmp/dbt_logs "
            "--select staging intermediate customer_360"
        ),
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            "cd /opt/project/dbt && "
            "dbt test --target-path /tmp/dbt_target --log-path /tmp/dbt_logs "
            "--select customer_360"
        ),
    )

    dlt_ingestion >> gx_validation >> dbt_run >> dbt_test