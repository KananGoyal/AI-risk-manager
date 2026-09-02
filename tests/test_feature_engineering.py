import pytest
import pandas as pd
from src.person_a.feature_engineering import compute_features, FEATURE_COLUMNS

def test_compute_features_keys():
    txn = {
        "timestamp": "2026-01-15 12:00:00",
        "merchant": "fraud_Vandervort_Tech",
        "merchant_category": "shopping_net",
        "amount": 250.0,
        "card_num": "4532_1234_5678",
        "device_id": "DEV_001",
        "declined": 0
    }
    feats = compute_features(txn)
    for col in FEATURE_COLUMNS:
        assert col in feats, f"Missing feature column: {col}"
    assert feats["amount"] == 250.0

def test_rolling_window_history():
    txn = {
        "timestamp": "2026-01-15 12:05:00",
        "merchant": "fraud_Vandervort_Tech",
        "merchant_category": "shopping_net",
        "amount": 500.0,
        "card_num": "4532_1234_5678",
        "device_id": "DEV_001",
        "declined": 1
    }
    history = [
        {
            "timestamp": "2026-01-15 12:01:00",
            "merchant": "fraud_Vandervort_Tech",
            "amount": 100.0,
            "card_num": "4532_1234_5678",
            "device_id": "DEV_001",
            "declined": 0
        }
    ]
    feats = compute_features(txn, history)
    assert feats["merchant_txn_cnt_5m"] == 2.0
    assert feats["merchant_amt_sum_5m"] == 600.0
