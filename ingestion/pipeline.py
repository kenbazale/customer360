"""
pipeline.py
Ingests the four synthetic banking CSVs into an S3 raw landing zone as
Parquet, partitioned by table and load date. This simulates pulling daily
extracts from a core banking system into a data lake.

Layout produced in the bucket:
  s3://bazale-customer360-raw/customer360_raw/customers/<load_id>/*.parquet
  s3://bazale-customer360-raw/customer360_raw/accounts/<load_id>/*.parquet
  s3://bazale-customer360-raw/customer360_raw/card_transactions/<load_id>/*.parquet
  s3://bazale-customer360-raw/customer360_raw/digital_events/<load_id>/*.parquet

Usage:
  python3 pipeline.py
"""

import os
import shutil
from pathlib import Path

import dlt
import pandas as pd

# Inside Airflow container, generator is mounted at /opt/project/generator
# When running locally, set CUSTOMER360_SOURCE_DIR env var to override
SOURCE_DIR = os.environ.get("CUSTOMER360_SOURCE_DIR", "/opt/project/generator")
PIPELINE_NAME = "customer360_raw_landing"

# Raw landing zone intentionally has NO primary key / not-null enforcement.
# Source data is dirty by nature (nulls, dupes, orphaned FKs) — that's the
# whole point of the data quality layer downstream. Constraints get applied
# later in dbt models / Great Expectations, never at raw ingestion.
TABLES = ["customers", "accounts", "card_transactions", "digital_events"]


@dlt.source
def banking_extract_source():
    for table_name in TABLES:

        @dlt.resource(name=table_name, write_disposition="replace")
        def load_table(table_name=table_name):
            df = pd.read_csv(f"{SOURCE_DIR}/{table_name}.csv")
            yield df.to_dict(orient="records")

        yield load_table


def reset_local_pipeline_state():
    """
    dlt keeps local working state (including in-progress load packages) in
    ~/.dlt/pipelines/<pipeline_name>/. If a previous run was interrupted
    (e.g. a container restart mid-load), stale packages left there can
    cause "package could not be found" errors on the next run.

    Wiping this directory before every run is the reliable fix: it's dlt's
    actual public working-directory location (not an internal API that
    could change between versions), and dlt recreates it automatically on
    the next pipeline.run() call. Since the pipeline is always re-run from
    the full source CSVs (write_disposition="replace"), there's no state
    worth preserving between runs anyway.
    """
    working_dir = Path.home() / ".dlt" / "pipelines" / PIPELINE_NAME
    if working_dir.exists():
        print(f"Clearing local dlt pipeline state at {working_dir}")
        shutil.rmtree(working_dir, ignore_errors=True)


def run():
    reset_local_pipeline_state()

    pipeline = dlt.pipeline(
        pipeline_name=PIPELINE_NAME,
        destination="filesystem",
        dataset_name="customer360_raw",
    )

    load_info = pipeline.run(banking_extract_source(), loader_file_format="parquet")
    print(load_info)
    return load_info


if __name__ == "__main__":
    run()