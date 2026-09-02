"""
clean_data.py - Load and clean transaction stream dataset (Sparkov schema),
normalizing column names, datatypes, and timestamps.

Output:
    data/processed/clean_transactions.csv
"""

import os
import sys
import numpy as np
import pandas as pd

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

RAW_DIR = os.path.join(_PROJECT_ROOT, "data", "raw")
PROCESSED_DIR = os.path.join(_PROJECT_ROOT, "data", "processed")
CLEAN_CSV = os.path.join(PROCESSED_DIR, "clean_transactions.csv")


def generate_synthetic_sparkov_base(n_samples: int = 15000, seed: int = 42) -> pd.DataFrame:
    """Generate a realistic base Sparkov-like transaction dataset if raw CSV is missing."""
    np.random.seed(seed)
    print(f"[clean_data] Generating realistic synthetic base transactions ({n_samples} rows)...")

    start_ts = pd.Timestamp("2026-01-01 00:00:00")
    # Generate realistic timestamps across 30 days
    seconds_offset = np.sort(np.random.randint(0, 30 * 24 * 3600, n_samples))
    timestamps = [start_ts + pd.Timedelta(seconds=int(s)) for s in seconds_offset]

    merchants = [
        "fraud_Kirlin_Inc", "fraud_Rippin_LLC", "fraud_Boyer_Group", "fraud_Kihn_Inc",
        "fraud_Schumm_Group", "fraud_Bednar_Inc", "fraud_Gould_Group", "fraud_Cruickshank_Apparel",
        "fraud_Vandervort_Tech", "fraud_Weber_Market", "fraud_Baumbach_Stores", "fraud_Heller_Gas"
    ]
    categories = [
        "grocery_pos", "entertainment", "gas_transport", "shopping_net",
        "misc_net", "grocery_net", "travel", "health_fitness"
    ]
    cities = ["New York, NY", "San Francisco, CA", "Chicago, IL", "Austin, TX", "Miami, FL", "Seattle, WA"]

    merchant_choices = np.random.choice(merchants, n_samples)
    category_choices = np.random.choice(categories, n_samples)
    amounts = np.round(np.random.exponential(scale=65.0, size=n_samples) + 2.50, 2)
    # Give high amounts to online categories
    for i in range(n_samples):
        if category_choices[i] in ["shopping_net", "travel", "misc_net"]:
            if np.random.rand() < 0.2:
                amounts[i] = np.round(np.random.uniform(250.0, 1200.0), 2)

    card_numbers = [f"4532_{np.random.randint(1000, 9999)}_{np.random.randint(1000, 9999)}" for _ in range(300)]
    card_choices = np.random.choice(card_numbers, n_samples)
    device_ids = [f"DEV_{np.random.randint(10000, 99999)}" for _ in range(500)]
    device_choices = np.random.choice(device_ids, n_samples)

    locations = np.random.choice(cities, n_samples)
    
    # Base organic fraud ~1.5%
    is_fraud = (np.random.rand(n_samples) < 0.015).astype(int)
    # High amounts + online shop increase organic fraud probability slightly
    for i in range(n_samples):
        if amounts[i] > 500.0 and category_choices[i] in ["shopping_net", "travel"]:
            if np.random.rand() < 0.15:
                is_fraud[i] = 1

    df = pd.DataFrame({
        "timestamp": timestamps,
        "merchant": merchant_choices,
        "merchant_category": category_choices,
        "amount": amounts,
        "cardholder_location": locations,
        "card_num": card_choices,
        "device_id": device_choices,
        "is_fraud": is_fraud,
    })
    return df


def load_and_clean_transactions(raw_dir: str = RAW_DIR) -> pd.DataFrame:
    """Load raw transaction dataset or generate synthetic baseline, then normalize."""
    os.makedirs(raw_dir, exist_ok=True)
    csv_files = [f for f in os.listdir(raw_dir) if f.endswith(".csv")]

    if csv_files:
        raw_path = os.path.join(raw_dir, csv_files[0])
        print(f"[clean_data] Loading raw data from {raw_path}...")
        df = pd.read_csv(raw_path)
        
        # Column remapping if Kaggle raw format
        rename_map = {
            "trans_date_trans_time": "timestamp",
            "amt": "amount",
            "category": "merchant_category",
            "cc_num": "card_num",
            "city_pop": "city_pop",
        }
        df = df.rename(columns=rename_map)
        
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        else:
            df["timestamp"] = pd.to_datetime("2026-01-01")
            
        required_cols = ["timestamp", "merchant", "merchant_category", "amount", "cardholder_location", "card_num", "device_id", "is_fraud"]
        for col in required_cols:
            if col not in df.columns:
                if col == "cardholder_location":
                    df[col] = "New York, NY"
                elif col == "device_id":
                    df[col] = "DEV_DEFAULT"
                elif col == "is_fraud":
                    df[col] = df.get("is_fraud", 0)
    else:
        df = generate_synthetic_sparkov_base()

    # Data formatting & sorting
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["transaction_id"] = [f"TXN-{i+10001:06d}" for i in range(len(df))]
    df["amount"] = df["amount"].astype(float).round(2)
    df["is_fraud"] = df["is_fraud"].astype(int)

    print(f"[clean_data] Processed dataset shape: {df.shape}")
    print(f"[clean_data] Fraud ratio: {df['is_fraud'].mean():.2%}")
    return df


def main():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    df = load_and_clean_transactions()
    df.to_csv(CLEAN_CSV, index=False)
    print(f"[clean_data] [OK] Clean transaction dataset saved to {CLEAN_CSV}")


if __name__ == "__main__":
    main()
