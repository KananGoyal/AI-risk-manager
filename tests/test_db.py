import pytest
import os
from src.db import init_db, save_scored_transaction, get_live_transactions, get_transaction_by_id

def test_db_read_write():
    init_db()
    record = {
        "transaction_id": "TEST-DB-001",
        "timestamp": "2026-01-20 10:00:00",
        "merchant": "fraud_Vandervort_Tech",
        "merchant_category": "shopping_net",
        "amount": 999.0,
        "card_num": "4532_0000",
        "device_id": "DEV_TEST",
        "risk_score": 0.85,
        "risk_band": "high",
        "action": "hold_for_verification",
        "cohort_context": {"historical_mean_amount": 65.0},
        "top_features": {"zscore": 3.5},
        "explanation": "Test explanation string.",
        "threshold_used": 0.35,
        "estimated_fp_cost": 1098.9,
        "estimated_fraud_caught": 999.0
    }

    save_scored_transaction(record)
    fetched = get_transaction_by_id("TEST-DB-001")

    assert fetched is not None
    assert fetched["transaction_id"] == "TEST-DB-001"
    assert fetched["risk_score"] == 0.85
    assert fetched["action"] == "hold_for_verification"
    assert fetched["explanation"] == "Test explanation string."
