"""
generate_accounts.py
Generates a synthetic 'accounts' table (savings/current/loan) linked to
customers.customer_id. 1-3 accounts per customer, weighted so most
customers have a savings account and a smaller share also carry a loan.
"""

import random
import uuid
from datetime import date, timedelta

import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(43)

ACCOUNT_TYPE_WEIGHTS = ["savings"] * 5 + ["current"] * 3 + ["loan"] * 2
PRODUCT_CODES = {
    "savings": ["SAV-STD", "SAV-PREMIUM", "SAV-YOUTH"],
    "current": ["CUR-STD", "CUR-BUSINESS"],
    "loan": ["LOAN-PERSONAL", "LOAN-MORTGAGE", "LOAN-AUTO"],
}
STATUS_WEIGHTS = ["active"] * 8 + ["dormant"] * 2 + ["closed"] * 1


def random_date_between(start_year, end_year):
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def generate_accounts(customers_df, broken_records=20):
    rows = []
    valid_customer_ids = customers_df["customer_id"].dropna().unique().tolist()

    for customer_id in customers_df["customer_id"]:
        if pd.isna(customer_id):
            continue  # skip customers with broken null IDs, mirrors real-world FK gaps
        n_accounts = random.choices([1, 2, 3], weights=[5, 3, 2])[0]
        chosen_types = random.sample(
            ACCOUNT_TYPE_WEIGHTS, min(n_accounts, len(ACCOUNT_TYPE_WEIGHTS))
        )
        for acc_type in chosen_types:
            status = random.choice(STATUS_WEIGHTS)
            open_date = random_date_between(2010, 2026)

            balance = round(random.uniform(-500, 50000), 2) if acc_type != "loan" \
                else round(random.uniform(1000, 80000), 2)

            loan_dpd = None
            if acc_type == "loan":
                # most loans current, some in arrears
                loan_dpd = random.choices(
                    [0, random.randint(1, 30), random.randint(31, 90), random.randint(91, 180)],
                    weights=[7, 1, 1, 1],
                )[0]

            rows.append(
                {
                    "account_id": str(uuid.uuid4()),
                    "customer_id": customer_id,
                    "account_type": acc_type,
                    "product_code": random.choice(PRODUCT_CODES[acc_type]),
                    "open_date": open_date.isoformat(),
                    "balance": balance,
                    "status": status,
                    "loan_days_past_due": loan_dpd,
                }
            )

    df = pd.DataFrame(rows)

    # --- Inject broken records for data quality tests ---
    broken_idx = random.sample(range(len(df)), min(broken_records, len(df)))
    for i, idx in enumerate(broken_idx):
        fault = i % 4
        if fault == 0:
            df.loc[idx, "customer_id"] = str(uuid.uuid4())  # orphaned FK, no matching customer
        elif fault == 1:
            df.loc[idx, "account_type"] = "unknown_type"  # invalid category
        elif fault == 2:
            df.loc[idx, "balance"] = None  # null balance
        elif fault == 3:
            df.loc[idx, "account_id"] = None  # null primary key

    return df


if __name__ == "__main__":
    customers_df = pd.read_csv("/home/claude/customer360/generator/customers.csv")
    df = generate_accounts(customers_df)
    df.to_csv("/home/claude/customer360/generator/accounts.csv", index=False)
    print(f"Generated {len(df)} accounts -> accounts.csv")
    print(df.head())
