"""
run_all.py
Runs all four generators in dependency order:
customers -> accounts -> card_transactions -> digital_events

Usage: python3 run_all.py
"""

import pandas as pd

from generate_customers import generate_customers
from generate_accounts import generate_accounts
from generate_card_transactions import generate_card_transactions
from generate_digital_events import generate_digital_events

OUT_DIR = "/home/claude/customer360/generator"


def main():
    customers_df = generate_customers()
    customers_df.to_csv(f"{OUT_DIR}/customers.csv", index=False)
    print(f"customers.csv       -> {len(customers_df)} rows")

    accounts_df = generate_accounts(customers_df)
    accounts_df.to_csv(f"{OUT_DIR}/accounts.csv", index=False)
    print(f"accounts.csv        -> {len(accounts_df)} rows")

    txns_df = generate_card_transactions(accounts_df)
    txns_df.to_csv(f"{OUT_DIR}/card_transactions.csv", index=False)
    print(f"card_transactions.csv -> {len(txns_df)} rows")

    events_df = generate_digital_events(customers_df)
    events_df.to_csv(f"{OUT_DIR}/digital_events.csv", index=False)
    print(f"digital_events.csv  -> {len(events_df)} rows")

    print("\nAll four tables generated successfully.")


if __name__ == "__main__":
    main()
