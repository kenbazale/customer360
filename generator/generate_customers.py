"""
generate_customers.py
Generates a synthetic 'customers' table mimicking a retail bank CIF (Customer
Information File) extract. Distributions are intentionally skewed to look
like a real bank's book, not a uniform random dataset.
"""

import random
import uuid
from datetime import date, timedelta

import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

N_CUSTOMERS = 2000

BRANCH_CODES = [f"BR{str(i).zfill(3)}" for i in range(1, 61)]  # 60 branches
SEGMENTS = ["retail", "retail", "retail", "SME", "premium"]  # weighted: retail most common
KYC_STATUSES = ["complete"] * 7 + ["pending"] * 2 + ["expired"] * 1  # weighted


def random_date_between(start_year, end_year):
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def generate_customers(n=N_CUSTOMERS, broken_records=15):
    rows = []
    for _ in range(n):
        dob = random_date_between(1950, 2005)
        customer_since = random_date_between(2010, 2026)

        rows.append(
            {
                "customer_id": str(uuid.uuid4()),
                "full_name": fake.name(),
                "dob": dob.isoformat(),
                "national_id_masked": f"XXXX-XXXX-{random.randint(1000,9999)}",
                "branch_code": random.choice(BRANCH_CODES),
                "kyc_status": random.choice(KYC_STATUSES),
                "customer_since_date": customer_since.isoformat(),
                "segment": random.choice(SEGMENTS),
            }
        )

    df = pd.DataFrame(rows)

    # --- Intentionally inject broken/dirty records for data quality tests ---
    # These simulate the kind of mess you'd actually find in a core banking
    # extract, and give you real failures to catch in Great Expectations/dbt tests.
    broken_idx = random.sample(range(len(df)), broken_records)

    for i, idx in enumerate(broken_idx):
        fault = i % 5
        if fault == 0:
            df.loc[idx, "customer_id"] = None  # null primary key
        elif fault == 1:
            df.loc[idx, "kyc_status"] = "unknown"  # invalid category
        elif fault == 2:
            df.loc[idx, "dob"] = "2031-01-01"  # future DOB
        elif fault == 3:
            df.loc[idx, "branch_code"] = "BR999"  # branch code not in valid list
        elif fault == 4:
            # duplicate customer_id (breaks uniqueness test)
            dup_source = random.choice([j for j in range(len(df)) if j != idx])
            df.loc[idx, "customer_id"] = df.loc[dup_source, "customer_id"]

    return df


if __name__ == "__main__":
    df = generate_customers()
    df.to_csv("/home/claude/customer360/generator/customers.csv", index=False)
    print(f"Generated {len(df)} customers -> customers.csv")
    print(df.head())
