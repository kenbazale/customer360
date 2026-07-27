"""
generate_card_transactions.py
Generates synthetic card transactions (ATM/POS) linked to accounts.account_id.
Mimics ISO 8583-style response codes so the "response_code" field feels real
rather than a plain boolean approve/decline flag.
"""

import random
import uuid
from datetime import datetime, timedelta

import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(44)

N_TRANSACTIONS = 50000

CHANNELS = ["POS"] * 6 + ["ATM"] * 4
MERCHANT_CATEGORIES = [
    "grocery", "fuel", "restaurant", "utilities", "retail",
    "pharmacy", "atm_withdrawal", "online", "transport", "entertainment",
]
# ISO 8583-style response codes: 00 = approved, others = various declines
RESPONSE_CODES = (
    ["00"] * 90  # approved
    + ["51"] * 4  # insufficient funds
    + ["05"] * 2  # do not honor
    + ["14"] * 2  # invalid card number
    + ["61"] * 1  # exceeds withdrawal limit
    + ["91"] * 1  # issuer unavailable
)


def random_datetime_within_days(days_back=365):
    now = datetime(2026, 7, 20)
    delta_seconds = random.randint(0, days_back * 24 * 3600)
    return now - timedelta(seconds=delta_seconds)


def generate_card_transactions(accounts_df, n=N_TRANSACTIONS, broken_records=40):
    # Only non-loan accounts realistically carry cards
    card_eligible = accounts_df[
        accounts_df["account_type"].isin(["savings", "current"])
        & accounts_df["account_id"].notna()
    ]["account_id"].tolist()

    rows = []
    for _ in range(n):
        account_id = random.choice(card_eligible)
        channel = random.choice(CHANNELS)
        merchant_cat = "atm_withdrawal" if channel == "ATM" else random.choice(
            [m for m in MERCHANT_CATEGORIES if m != "atm_withdrawal"]
        )
        amount = round(random.uniform(2, 40) if merchant_cat == "grocery"
                        else random.uniform(5, 800), 2)

        rows.append(
            {
                "txn_id": str(uuid.uuid4()),
                "account_id": account_id,
                "txn_datetime": random_datetime_within_days().isoformat(),
                "channel": channel,
                "amount": amount,
                "merchant_category": merchant_cat,
                "response_code": random.choice(RESPONSE_CODES),
            }
        )

    df = pd.DataFrame(rows)

    # --- Inject broken records ---
    broken_idx = random.sample(range(len(df)), min(broken_records, len(df)))
    for i, idx in enumerate(broken_idx):
        fault = i % 3
        if fault == 0:
            df.loc[idx, "amount"] = -999.99  # invalid negative amount
        elif fault == 1:
            df.loc[idx, "account_id"] = str(uuid.uuid4())  # orphaned FK
        elif fault == 2:
            df.loc[idx, "response_code"] = "XX"  # invalid response code

    return df


if __name__ == "__main__":
    accounts_df = pd.read_csv("/home/claude/customer360/generator/accounts.csv")
    df = generate_card_transactions(accounts_df)
    df.to_csv("/home/claude/customer360/generator/card_transactions.csv", index=False)
    print(f"Generated {len(df)} card transactions -> card_transactions.csv")
    print(df.head())
