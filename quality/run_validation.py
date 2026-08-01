"""
run_validation.py
Pre-load data quality gate for the raw banking extracts, using Great
Expectations. This runs BEFORE the dlt ingestion step in the pipeline and
produces a human-readable HTML report (Data Docs) — the kind of artifact a
real bank's data ops team would check each morning before a batch load
proceeds.
 
This is deliberately a *reporting* gate, not a *blocking* one: like the
staging-layer dbt tests, it's meant to surface known issues in the source
extract (nulls, invalid categories, out-of-range values) without stopping
the pipeline — that's the raw layer's job. It complements, rather than
duplicates, the dbt tests: GX validates the extract before it's loaded
anywhere; dbt tests validate the transformed data inside the warehouse.
 
Usage:
    python3 run_validation.py
"""