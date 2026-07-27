"""
generate_digital_events.py
Generates synthetic digital channel events (mobile/web logins, transfers,
bill pay) linked to customers.customer_id. Distribution is deliberately
uneven: a subset of customers are heavy digital users, a chunk barely
touch digital channels at all (feeds the "engagement score" logic later).
"""

import random
import uuid
from datetime import datetime, timedelta

import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(45)

N_EVENTS = 30000

CHANNELS = ["mobile"] * 7 + ["web"] * 3
EVENT_TYPES = ["login"] * 6 + ["transfer"] * 2 + ["bill_pay"] * 2


def random_datetime_within_days(days_back=365):
    now = datetime(2026, 7, 20)
    delta_seconds = random.randint(0, days_back * 24 * 3600)
    return now - timedelta(seconds=delta_seconds)


def generate_digital_events(customers_df, n=N_EVENTS, broken_records=25):
    valid_customer_ids = customers_df["customer_id"].dropna().tolist()

    # Split customers into "active digital users" (get most events) vs
    # "low/no digital engagement" (get few or none) — mirrors real adoption gaps
    random.shuffle(valid_customer_ids)
    split_point = int(len(valid_customer_ids) * 0.35)
    active_users = valid_customer_ids[:split_point]
    low_users = valid_customer_ids[split_point:]

    rows = []
    for _ in range(n):
        # 85% of events come from the active-user segment
        customer_id = random.choice(active_users) if random.random() < 0.85 else random.choice(low_users)
        rows.append(
            {
                "event_id": str(uuid.uuid4()),
                "customer_id": customer_id,
                "event_datetime": random_datetime_within_days().isoformat(),
                "channel": random.choice(CHANNELS),
                "event_type": random.choice(EVENT_TYPES),
            }
        )

    df = pd.DataFrame(rows)

    # --- Inject broken records ---
    broken_idx = random.sample(range(len(df)), min(broken_records, len(df)))
    for i, idx in enumerate(broken_idx):
        fault = i % 3
        if fault == 0:
            df.loc[idx, "customer_id"] = str(uuid.uuid4())  # orphaned FK
        elif fault == 1:
            df.loc[idx, "event_type"] = "unknown_event"  # invalid category
        elif fault == 2:
            df.loc[idx, "event_datetime"] = "2031-01-01T00:00:00"  # future timestamp

    return df


if __name__ == "__main__":
    customers_df = pd.read_csv("/home/claude/customer360/generator/customers.csv")
    df = generate_digital_events(customers_df)
    df.to_csv("/home/claude/customer360/generator/digital_events.csv", index=False)
    print(f"Generated {len(df)} digital events -> digital_events.csv")
    print(df.head())
