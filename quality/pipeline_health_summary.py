"""
pipeline_health_summary.py
Runs as the final task in the DAG, after dbt_test succeeds. Queries the
customer_360 mart directly and writes a structured, timestamped snapshot
to a local log file - the kind of "is the pipeline actually healthy today"
artifact a data platform team would check without needing to open
Snowflake or read through Airflow task logs individually.

Reuses the same profiles.yml already mounted into the container for dbt,
rather than duplicating Snowflake credentials in a second place.

Usage (inside the Airflow container):
    python3 pipeline_health_summary.py
"""

import json
import os
from datetime import datetime, timezone

import snowflake.connector
import yaml

PROFILES_PATH = "/opt/project/dbt_profiles/profiles.yml"
HEALTH_LOG_PATH = "/opt/airflow/logs/pipeline_health.jsonl"


def load_snowflake_connection():
    with open(PROFILES_PATH) as f:
        profiles = yaml.safe_load(f)

    profile = profiles["customer360_dbt"]
    target_name = profile["target"]
    target = profile["outputs"][target_name]

    return snowflake.connector.connect(
        account=target["account"],
        user=target["user"],
        password=target["password"],
        warehouse=target["warehouse"],
        database=target["database"],
        schema="mart",
        role=target["role"],
    )


def run():
    conn = load_snowflake_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM mart.customer_360")
    total_customers = cur.fetchone()[0]

    cur.execute(
        """
        SELECT dormancy_risk, COUNT(*)
        FROM mart.customer_360
        GROUP BY dormancy_risk
        """
    )
    dormancy_distribution = {row[0]: row[1] for row in cur.fetchall()}

    cur.execute(
        """
        SELECT delinquency_status, COUNT(*)
        FROM mart.customer_360
        GROUP BY delinquency_status
        """
    )
    delinquency_distribution = {row[0]: row[1] for row in cur.fetchall()}

    cur.execute("SELECT AVG(engagement_score) FROM mart.customer_360")
    avg_engagement = round(float(cur.fetchone()[0]), 2)

    summary = {
        "event": "pipeline_health_summary",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_customers": total_customers,
        "dormancy_distribution": dormancy_distribution,
        "delinquency_distribution": delinquency_distribution,
        "avg_engagement_score": avg_engagement,
    }

    os.makedirs(os.path.dirname(HEALTH_LOG_PATH), exist_ok=True)
    with open(HEALTH_LOG_PATH, "a") as f:
        f.write(json.dumps(summary) + "\n")

    print(json.dumps(summary, indent=2))

    cur.close()
    conn.close()


if __name__ == "__main__":
    run()