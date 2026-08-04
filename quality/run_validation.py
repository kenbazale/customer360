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

import sys

import great_expectations as gx
import pandas as pd

SOURCE_DIR = "/opt/project/generator"


def reset_pandas_datasource(context, name):
    """Delete the datasource if it exists, then create it fresh. Ensures
    each run reflects exactly what's defined in this file, rather than
    silently accumulating duplicate expectations across repeated runs
    (this script is designed to be called daily by Airflow)."""
    try:
        context.data_sources.delete(name)
    except Exception:
        pass
    return context.data_sources.add_pandas(name)


def reset_suite(context, suite_obj):
    try:
        context.suites.delete(suite_obj.name)
    except Exception:
        pass
    return context.suites.add(suite_obj)


def reset_validation_definition(context, validation_def_obj):
    try:
        context.validation_definitions.delete(validation_def_obj.name)
    except Exception:
        pass
    return context.validation_definitions.add(validation_def_obj)


def reset_checkpoint(context, checkpoint_obj):
    try:
        context.checkpoints.delete(checkpoint_obj.name)
    except Exception:
        pass
    return context.checkpoints.add(checkpoint_obj)


def build_customers_suite(context):
    df = pd.read_csv(f"{SOURCE_DIR}/customers.csv")

    data_source = reset_pandas_datasource(context, "customers_source")
    data_asset = data_source.add_dataframe_asset(name="customers")
    batch_def = data_asset.add_batch_definition_whole_dataframe("customers_batch")

    suite = reset_suite(context, gx.ExpectationSuite(name="customers_suite"))

    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=1, max_value=1_000_000)
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="customer_id")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeUnique(column="customer_id")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnDistinctValuesToBeInSet(
            column="kyc_status",
            value_set=["complete", "pending", "expired"],
        )
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnDistinctValuesToBeInSet(
            column="segment", value_set=["retail", "SME", "premium"]
        )
    )

    return batch_def, suite, df


def build_accounts_suite(context):
    df = pd.read_csv(f"{SOURCE_DIR}/accounts.csv")

    data_source = reset_pandas_datasource(context, "accounts_source")
    data_asset = data_source.add_dataframe_asset(name="accounts")
    batch_def = data_asset.add_batch_definition_whole_dataframe("accounts_batch")

    suite = reset_suite(context, gx.ExpectationSuite(name="accounts_suite"))

    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="account_id")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnDistinctValuesToBeInSet(
            column="account_type",
            value_set=["savings", "current", "loan"],
        )
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="balance", min_value=-1000, max_value=200_000
        )
    )

    return batch_def, suite, df


def build_card_transactions_suite(context):
    df = pd.read_csv(f"{SOURCE_DIR}/card_transactions.csv")

    data_source = reset_pandas_datasource(context, "card_transactions_source")
    data_asset = data_source.add_dataframe_asset(name="card_transactions")
    batch_def = data_asset.add_batch_definition_whole_dataframe("card_transactions_batch")

    suite = reset_suite(context, gx.ExpectationSuite(name="card_transactions_suite"))

    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="txn_id")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="amount", min_value=0, max_value=10_000
        )
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnDistinctValuesToBeInSet(
            column="response_code",
            value_set=["00", "51", "05", "14", "61", "91"],
        )
    )

    return batch_def, suite, df


def build_digital_events_suite(context):
    df = pd.read_csv(f"{SOURCE_DIR}/digital_events.csv")

    data_source = reset_pandas_datasource(context, "digital_events_source")
    data_asset = data_source.add_dataframe_asset(name="digital_events")
    batch_def = data_asset.add_batch_definition_whole_dataframe("digital_events_batch")

    suite = reset_suite(context, gx.ExpectationSuite(name="digital_events_suite"))

    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="event_id")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnDistinctValuesToBeInSet(
            column="event_type",
            value_set=["login", "transfer", "bill_pay"],
        )
    )

    return batch_def, suite, df


def run():
    context = gx.get_context(mode="file", project_root_dir=".")

    builders = {
        "customers": build_customers_suite,
        "accounts": build_accounts_suite,
        "card_transactions": build_card_transactions_suite,
        "digital_events": build_digital_events_suite,
    }

    results = {}
    validation_definitions = []

    for table_name, builder in builders.items():
        batch_def, suite, df = builder(context)

        validation_def = reset_validation_definition(
            context,
            gx.ValidationDefinition(
                name=f"{table_name}_validation",
                data=batch_def,
                suite=suite,
            )
        )
        validation_definitions.append(validation_def)

        result = validation_def.run(batch_parameters={"dataframe": df})
        results[table_name] = result

    # Build a checkpoint over all validation definitions so we get a single
    # combined Data Docs report across all four tables.
    checkpoint = reset_checkpoint(
        context,
        gx.Checkpoint(
            name="raw_extract_checkpoint",
            validation_definitions=validation_definitions,
            actions=[gx.checkpoint.UpdateDataDocsAction(name="update_data_docs")],
        )
    )

    batch_parameters_by_definition = {
        vd.id: {"dataframe": pd.read_csv(f"{SOURCE_DIR}/{name}.csv")}
        for vd, name in zip(validation_definitions, builders.keys())
    }

    print("\n" + "=" * 70)
    print("RAW EXTRACT DATA QUALITY REPORT")
    print("=" * 70)

    total_failed = 0
    for table_name, result in results.items():
        success = result.success
        stats = result.statistics
        status = "PASS" if success else "ISSUES FOUND"
        print(
            f"\n{table_name:20s} [{status}] "
            f"{stats['successful_expectations']}/{stats['evaluated_expectations']} "
            f"expectations met"
        )
        if not success:
            total_failed += 1
            for res in result.results:
                if not res.success:
                    exp_type = res.expectation_config.type
                    col = res.expectation_config.kwargs.get("column", "")
                    unexpected = res.result.get("unexpected_count", "?")
                    print(f"    - {exp_type} on '{col}': {unexpected} unexpected values")

    print("\n" + "=" * 70)
    if total_failed:
        print(f"{total_failed} of 4 tables had data quality issues (expected — see above)")
    else:
        print("All tables passed cleanly")
    print("=" * 70)

    context.build_data_docs()
    print("\nData Docs built. Open great_expectations/uncommitted/data_docs/local_site/index.html")

    return 0


if __name__ == "__main__":
    sys.exit(run())