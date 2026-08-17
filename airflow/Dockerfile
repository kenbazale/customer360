# Extends the official Airflow image with the project's data stack, so
# BashOperator tasks in the DAG can call pipeline.py, run_validation.py,
# and dbt directly inside the Airflow worker container.

FROM apache/airflow:2.9.3-python3.12

USER airflow

RUN pip install --no-cache-dir \
    "dlt[filesystem,s3,parquet]" \
    great_expectations \
    dbt-snowflake \
    pyyaml \
    requests