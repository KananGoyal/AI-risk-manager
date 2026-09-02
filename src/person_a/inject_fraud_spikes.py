"""
inject_fraud_spikes.py - Controlled synthetic fraud burst injection for reproducible demo spikes.

Three burst types:
1. inject_card_testing(): Many micro-transactions ($1.00-$5.00) in a tight window.
2. inject_account_takeover(): High-value transactions after sudden device/location switch.
3. inject_velocity_abuse(): Rapid multi-merchant transactions using the same card/instrument.
"""

import os
import sys
import numpy as np
import pandas as pd

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

PROCESSED_DIR = os.path.join(_PROJECT_ROOT, "data", "processed")
CLEAN_CSV = os.path.join(PROCESSED_DIR, "clean_transactions.csv")
INJECTED_CSV = os.path.join(PROCESSED_DIR, "injected_transactions.csv")


def inject_card_testing(
    df: pd.DataFrame,
    target_merchant: str = "fraud_Vandervort_Tech",
    n_bursts: int = 25,
    start_time: pd.Timestamp = pd.Timestamp("2026-01-15 14:00:00"),
    seed: int = 42,
) -> pd.DataFrame:
    """Inject card testing burst: rapid micro-transactions over 15 minutes."""
    np.random.seed(seed)
    burst_rows = []
    card_test_num = f"4532_{seed}_CARDTEST"
    device_test = f"DEV_TESTING_{seed}"

    for i in range(n_bursts):
        offset_sec = int(i * 30 + np.random.randint(0, 10))
        ts = start_time + pd.Timedelta(seconds=offset_sec)
        amount = round(float(np.random.uniform(0.99, 4.99)), 2)
        burst_rows.append({
            "timestamp": ts,
            "merchant": target_merchant,
            "merchant_category": "shopping_net",
            "amount": amount,
            "cardholder_location": "Miami, FL",
            "card_num": card_test_num,
            "device_id": device_test,
            "is_fraud": 1,
            "spike_type": "card_testing",
            "declined": 1 if np.random.rand() < 0.7 else 0
        })

    burst_df = pd.DataFrame(burst_rows)
    combined = pd.concat([df, burst_df], ignore_index=True)
    return combined.sort_values("timestamp").reset_index(drop=True)


def inject_account_takeover(
    df: pd.DataFrame,
    target_card: str = None,
    n_bursts: int = 5,
    start_time: pd.Timestamp = pd.Timestamp("2026-01-20 22:15:00"),
    seed: int = 43,
) -> pd.DataFrame:
    """Inject account takeover burst: sudden high-value purchases from foreign device/location."""
    np.random.seed(seed)
    if target_card is None:
        target_card = df["card_num"].iloc[0]

    burst_rows = []
    ato_device = f"DEV_ATO_FOREIGN_{seed}"
    high_risk_merchants = ["fraud_Kirlin_Inc", "fraud_Vandervort_Tech", "fraud_Cruickshank_Apparel"]

    for i in range(n_bursts):
        ts = start_time + pd.Timedelta(minutes=i * 4 + np.random.randint(0, 2))
        merchant = high_risk_merchants[i % len(high_risk_merchants)]
        amount = round(float(np.random.uniform(650.0, 2200.0)), 2)
        burst_rows.append({
            "timestamp": ts,
            "merchant": merchant,
            "merchant_category": "shopping_net",
            "amount": amount,
            "cardholder_location": "Foreign/VPN IP",
            "card_num": target_card,
            "device_id": ato_device,
            "is_fraud": 1,
            "spike_type": "account_takeover",
            "declined": 0
        })

    burst_df = pd.DataFrame(burst_rows)
    combined = pd.concat([df, burst_df], ignore_index=True)
    return combined.sort_values("timestamp").reset_index(drop=True)


def inject_velocity_abuse(
    df: pd.DataFrame,
    n_bursts: int = 15,
    start_time: pd.Timestamp = pd.Timestamp("2026-01-25 10:00:00"),
    seed: int = 44,
) -> pd.DataFrame:
    """Inject velocity abuse burst: rapid multi-merchant transactions using one payment instrument."""
    np.random.seed(seed)
    burst_rows = []
    velocity_card = f"4532_VELOCITY_ABUSE_{seed}"
    merchants = ["fraud_Rippin_LLC", "fraud_Boyer_Group", "fraud_Kihn_Inc", "fraud_Weber_Market", "fraud_Heller_Gas"]

    for i in range(n_bursts):
        ts = start_time + pd.Timedelta(seconds=i * 45 + np.random.randint(0, 15))
        merchant = merchants[i % len(merchants)]
        amount = round(float(np.random.uniform(120.0, 480.0)), 2)
        burst_rows.append({
            "timestamp": ts,
            "merchant": merchant,
            "merchant_category": "grocery_pos" if i % 2 == 0 else "shopping_net",
            "amount": amount,
            "cardholder_location": "Chicago, IL",
            "card_num": velocity_card,
            "device_id": f"DEV_VEL_{seed}",
            "is_fraud": 1,
            "spike_type": "velocity_abuse",
            "declined": 0
        })

    burst_df = pd.DataFrame(burst_rows)
    combined = pd.concat([df, burst_df], ignore_index=True)
    return combined.sort_values("timestamp").reset_index(drop=True)


def run_injection_pipeline(clean_csv_path: str = CLEAN_CSV, seed: int = 42) -> pd.DataFrame:
    """Execute all fraud burst injections deterministically."""
    print(f"[inject_fraud_spikes] Loading clean base data from {clean_csv_path}...")
    if not os.path.exists(clean_csv_path):
        from src.person_a.clean_data import main as clean_main
        clean_main()

    df = pd.read_csv(clean_csv_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    if "spike_type" not in df.columns:
        df["spike_type"] = "organic"
    if "declined" not in df.columns:
        df["declined"] = 0

    print("[inject_fraud_spikes] Injecting Card Testing burst...")
    df = inject_card_testing(df, seed=seed)

    print("[inject_fraud_spikes] Injecting Account Takeover burst...")
    df = inject_account_takeover(df, seed=seed + 1)

    print("[inject_fraud_spikes] Injecting Velocity Abuse burst...")
    df = inject_velocity_abuse(df, seed=seed + 2)

    # Re-assign clean IDs
    df["transaction_id"] = [f"TXN-{i+10001:06d}" for i in range(len(df))]
    print(f"[inject_fraud_spikes] Final dataset shape after injection: {df.shape}")
    print(f"[inject_fraud_spikes] Total fraud count: {df['is_fraud'].sum()} ({df['is_fraud'].mean():.2%})")
    return df


def main():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    df = run_injection_pipeline()
    df.to_csv(INJECTED_CSV, index=False)
    print(f"[inject_fraud_spikes] [OK] Saved injected transactions to {INJECTED_CSV}")


if __name__ == "__main__":
    main()
