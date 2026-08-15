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
import dlt
import pandas as pd


import os

SOURCE_DIR = os.environ.get("CUSTOMER360_SOURCE_DIR", "/home/claude/customer360/generator")
 
# Raw landing zone intentionally has NO primary key / not-null enforcement.
# Source data is dirty by nature (nulls, dupes, orphaned FKs) — that's the
# whole point of the data quality layer downstream. Constraints get applied
# later in dbt models / Great Expectations, never at raw ingestion.

TABLES = ["customers", "accounts", "card_transactions", "digital_events"]

@dlt.source
def banking_extract_source():
    for table_name in TABLES:
        @dlt.resource(name=table_name,write_disposition='replace')
        def load_table(table_name=table_name):
            df = pd.read_csv(f'{SOURCE_DIR}/{table_name}.csv')
            yield df.to_dict(orient='records')
        yield load_table


def run():
    pipeline = dlt.pipeline(
        pipeline_name='customer360_raw_landing',
        destination='filesystem',
        dataset_name='customer360_raw'
    )
    load_info = pipeline.run(banking_extract_source(), loader_file_format='parquet')

if __name__ == '__main__':
    run()