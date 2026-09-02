"""
feature_engineering.py - Rolling-window feature computation module.

Computes:
1. Rolling txn count/amount per merchant (5m, 1h, 24h)
2. Z-score deviation from historical baseline (same weekday/hour)
3. Decline rate within rolling window
4. Device & instrument diversity ratios
5. Category risk prior

Dual-use requirement:
Exposes compute_features(transaction, history_context) -> dict / feature_vector
callable both in batch mode (full dataset) and live mode (single transaction against recent history).
"""

import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Union

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

FEATURE_COLUMNS = [
    "amount",
    "merchant_txn_cnt_5m",
    "merchant_amt_sum_5m",
    "merchant_txn_cnt_1h",
    "merchant_amt_sum_1h",
    "merchant_txn_cnt_24h",
    "merchant_amt_sum_24h",
    "amount_baseline_zscore",
    "txn_count_baseline_zscore",
    "decline_rate_1h",
    "distinct_cards_per_device_24h",
    "distinct_devices_per_card_24h",
    "category_risk_prior",
]

CATEGORY_RISK_MAP = {
    "shopping_net": 0.08,
    "misc_net": 0.07,
    "travel": 0.06,
    "entertainment": 0.03,
    "grocery_net": 0.02,
    "grocery_pos": 0.01,
    "gas_transport": 0.01,
    "health_fitness": 0.01,
}


def compute_features(
    transaction: Dict[str, Any],
    history_context: Union[pd.DataFrame, List[Dict[str, Any]]] = None,
) -> Dict[str, float]:
    """Single-transaction feature calculation against recent history context.
    
    Returns a dictionary of normalized feature values suitable for model prediction.
    """
    ts = pd.to_datetime(transaction.get("timestamp", pd.Timestamp.now()))
    merchant = transaction.get("merchant", "unknown")
    category = transaction.get("merchant_category", "grocery_pos")
    amount = float(transaction.get("amount", 0.0))
    card_num = transaction.get("card_num", "")
    device_id = transaction.get("device_id", "")
    declined = int(transaction.get("declined", 0))

    if history_context is None or len(history_context) == 0:
        hist_df = pd.DataFrame()
    elif isinstance(history_context, list):
        hist_df = pd.DataFrame(history_context)
    else:
        hist_df = history_context.copy()

    if not hist_df.empty and "timestamp" in hist_df.columns:
        hist_df["timestamp"] = pd.to_datetime(hist_df["timestamp"])
        # Filter history up to current timestamp
        hist_df = hist_df[hist_df["timestamp"] <= ts]
    else:
        hist_df = pd.DataFrame(columns=["timestamp", "merchant", "amount", "card_num", "device_id", "declined"])

    # 1. Rolling merchant aggregates
    ts_5m = ts - pd.Timedelta(minutes=5)
    ts_1h = ts - pd.Timedelta(hours=1)
    ts_24h = ts - pd.Timedelta(hours=24)

    m_hist = hist_df[hist_df["merchant"] == merchant] if not hist_df.empty else pd.DataFrame()

    m_5m = m_hist[m_hist["timestamp"] >= ts_5m] if not m_hist.empty else pd.DataFrame()
    m_1h = m_hist[m_hist["timestamp"] >= ts_1h] if not m_hist.empty else pd.DataFrame()
    m_24h = m_hist[m_hist["timestamp"] >= ts_24h] if not m_hist.empty else pd.DataFrame()

    m_cnt_5m = float(len(m_5m) + 1)
    m_amt_5m = float(m_5m["amount"].sum() + amount) if not m_5m.empty else amount

    m_cnt_1h = float(len(m_1h) + 1)
    m_amt_1h = float(m_1h["amount"].sum() + amount) if not m_1h.empty else amount

    m_cnt_24h = float(len(m_24h) + 1)
    m_amt_24h = float(m_24h["amount"].sum() + amount) if not m_24h.empty else amount

    # 2. Historical same weekday/hour baseline z-score
    weekday = ts.weekday()
    hour = ts.hour
    if not m_hist.empty and len(m_hist) > 5:
        m_hist_baseline = m_hist[
            (m_hist["timestamp"].dt.weekday == weekday) & (m_hist["timestamp"].dt.hour == hour)
        ]
        if not m_hist_baseline.empty and len(m_hist_baseline) > 2:
            mean_amt = m_hist_baseline["amount"].mean()
            std_amt = m_hist_baseline["amount"].std()
            amt_zscore = float((amount - mean_amt) / (std_amt + 1e-5))
            cnt_zscore = float((m_cnt_1h - (len(m_hist_baseline) / 4.0)) / 2.0)
        else:
            amt_zscore = float((amount - 65.0) / 45.0)
            cnt_zscore = float((m_cnt_1h - 1.0) / 2.0)
    else:
        amt_zscore = float((amount - 65.0) / 45.0)
        cnt_zscore = float((m_cnt_1h - 1.0) / 2.0)

    # 3. Decline rate within 1h window
    if not m_1h.empty and "declined" in m_1h.columns:
        total_dec = m_1h["declined"].sum() + declined
        decline_rate_1h = float(total_dec / (len(m_1h) + 1))
    else:
        decline_rate_1h = float(declined)

    # 4. Device and Instrument diversity ratios
    dev_hist_24h = hist_df[(hist_df["device_id"] == device_id) & (hist_df["timestamp"] >= ts_24h)] if not hist_df.empty else pd.DataFrame()
    card_hist_24h = hist_df[(hist_df["card_num"] == card_num) & (hist_df["timestamp"] >= ts_24h)] if not hist_df.empty else pd.DataFrame()

    if not dev_hist_24h.empty and "card_num" in dev_hist_24h.columns:
        cards_per_dev = float(dev_hist_24h["card_num"].nunique())
        if card_num not in dev_hist_24h["card_num"].values:
            cards_per_dev += 1.0
    else:
        cards_per_dev = 1.0

    if not card_hist_24h.empty and "device_id" in card_hist_24h.columns:
        devs_per_card = float(card_hist_24h["device_id"].nunique())
        if device_id not in card_hist_24h["device_id"].values:
            devs_per_card += 1.0
    else:
        devs_per_card = 1.0

    # 5. Category risk prior
    category_prior = CATEGORY_RISK_MAP.get(category, 0.02)

    return {
        "amount": amount,
        "merchant_txn_cnt_5m": m_cnt_5m,
        "merchant_amt_sum_5m": m_amt_5m,
        "merchant_txn_cnt_1h": m_cnt_1h,
        "merchant_amt_sum_1h": m_amt_1h,
        "merchant_txn_cnt_24h": m_cnt_24h,
        "merchant_amt_sum_24h": m_amt_24h,
        "amount_baseline_zscore": amt_zscore,
        "txn_count_baseline_zscore": cnt_zscore,
        "decline_rate_1h": decline_rate_1h,
        "distinct_cards_per_device_24h": cards_per_dev,
        "distinct_devices_per_card_24h": devs_per_card,
        "category_risk_prior": category_prior,
    }


def compute_features_batch(df: pd.DataFrame) -> pd.DataFrame:
    """Efficient vector/rolling calculation across full DataFrame for training."""
    print(f"[feature_engineering] Computing batch rolling features for {len(df)} transactions...")
    df_sorted = df.sort_values("timestamp").copy()
    
    # Store calculated features
    feature_list = []
    
    # We maintain recent history window in memory for efficiency
    history_records = []
    
    for idx, row in df_sorted.iterrows():
        txn_dict = row.to_dict()
        feats = compute_features(txn_dict, history_records)
        feature_list.append(feats)
        
        # Append to history, keeping only last 24h worth of transactions
        ts = pd.to_datetime(row["timestamp"])
        history_records.append({
            "timestamp": ts,
            "merchant": row["merchant"],
            "amount": row["amount"],
            "card_num": row["card_num"],
            "device_id": row["device_id"],
            "declined": row.get("declined", 0)
        })
        
        # Prune old history > 24h
        cut_ts = ts - pd.Timedelta(hours=24)
        history_records = [r for r in history_records if r["timestamp"] >= cut_ts]
        
        if len(feature_list) % 5000 == 0:
            print(f"  Processed {len(feature_list)}/{len(df)} transactions...")

    feature_df = pd.DataFrame(feature_list)

    # Drop existing feature columns from df_sorted to avoid column name collisions
    df_base = df_sorted.reset_index(drop=True)
    cols_to_drop = [c for c in feature_df.columns if c in df_base.columns]
    if cols_to_drop:
        df_base = df_base.drop(columns=cols_to_drop)

    result_df = pd.concat([df_base, feature_df], axis=1)
    result_df = result_df.loc[:, ~result_df.columns.duplicated()].copy()
    print(f"[feature_engineering] Batch feature calculation complete. Total columns: {len(result_df.columns)}")
    return result_df


if __name__ == "__main__":
    test_txn = {
        "timestamp": "2026-01-15 14:00:00",
        "merchant": "fraud_Vandervort_Tech",
        "merchant_category": "shopping_net",
        "amount": 450.0,
        "card_num": "4532_1234_5678",
        "device_id": "DEV_9999",
        "declined": 0
    }
    feats = compute_features(test_txn)
    print("Test single feature vector:")
    for k, v in feats.items():
        print(f"  {k}: {v}")
