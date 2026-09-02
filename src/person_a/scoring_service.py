"""
scoring_service.py - Real-time transaction scoring engine with sub-millisecond cohort baselines.

Function:
    score_transaction(transaction_dict, history_context=None) -> Dict[str, Any]

Contract output:
    {
        "transaction_id": str,
        "risk_score": float (0.0 - 1.0),
        "features": Dict[str, float],
        "cohort_context": Dict[str, Any],
        "scoring_latency_ms": float
    }
"""

import os
import sys
import json
import time
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.person_a.feature_engineering import compute_features, FEATURE_COLUMNS

MODELS_DIR = os.path.join(_PROJECT_ROOT, "data", "models")
MODEL_PATH = os.path.join(MODELS_DIR, "fraud_model.joblib")
BASELINES_PATH = os.path.join(MODELS_DIR, "merchant_baselines.json")

_model = None
_baselines = None


def _load_resources():
    """Lazy load model and precomputed baselines into memory."""
    global _model, _baselines
    if _model is None:
        if os.path.exists(MODEL_PATH):
            try:
                _model = joblib.load(MODEL_PATH)
            except Exception as e:
                print(f"[scoring_service] Model load error: {e}")
                _model = None

    if _baselines is None:
        if os.path.exists(BASELINES_PATH):
            try:
                with open(BASELINES_PATH, "r") as f:
                    _baselines = json.load(f)
            except Exception as e:
                print(f"[scoring_service] Baselines load error: {e}")
                _baselines = {}
        else:
            _baselines = {}


def score_transaction(
    transaction: Dict[str, Any],
    history_context: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Score a single incoming transaction synchronously for real-time live feed."""
    start_t = time.time()
    _load_resources()

    # 1. Feature Engineering
    features = compute_features(transaction, history_context)
    feat_df = pd.DataFrame([features])[FEATURE_COLUMNS]

    # 2. ML Probability Inference
    if _model is not None:
        try:
            prob = float(_model.predict_proba(feat_df)[0, 1])
        except Exception as e:
            prob = _heuristic_scoring(transaction, features)
    else:
        prob = _heuristic_scoring(transaction, features)

    risk_score = float(np.clip(prob, 0.0, 1.0))

    # 3. Fast In-Memory Cohort Baseline Lookup (<1ms)
    merchant = transaction.get("merchant", "unknown")
    baseline = _baselines.get(merchant, _baselines.get("__GLOBAL_DEFAULT__", {
        "mean_amount": 65.0,
        "std_amount": 45.0,
        "txn_count_24h_avg": 5.0,
        "category": transaction.get("merchant_category", "grocery_pos"),
        "fraud_rate": 0.015
    }))

    amount = float(transaction.get("amount", 0.0))
    mean_amt = baseline.get("mean_amount", 65.0)
    ratio_to_baseline = round(amount / max(mean_amt, 1.0), 2)

    cohort_context = {
        "merchant": merchant,
        "merchant_category": transaction.get("merchant_category", "grocery_pos"),
        "historical_mean_amount": mean_amt,
        "historical_std_amount": baseline.get("std_amount", 45.0),
        "amount_ratio_vs_baseline": ratio_to_baseline,
        "baseline_zscore": features.get("amount_baseline_zscore", 0.0),
        "historical_fraud_rate": baseline.get("fraud_rate", 0.015),
    }

    elapsed_ms = round((time.time() - start_t) * 1000.0, 2)

    return {
        "transaction_id": transaction.get("transaction_id", f"TXN-{int(time.time()*1000)%1000000:06d}"),
        "timestamp": str(transaction.get("timestamp", pd.Timestamp.now())),
        "merchant": merchant,
        "amount": amount,
        "card_num": transaction.get("card_num", "UNKNOWN"),
        "device_id": transaction.get("device_id", "UNKNOWN"),
        "risk_score": round(risk_score, 4),
        "features": features,
        "cohort_context": cohort_context,
        "scoring_latency_ms": elapsed_ms
    }


def _heuristic_scoring(transaction: Dict[str, Any], features: Dict[str, float]) -> float:
    """Heuristic scoring fallback if ML model is unavailable."""
    score = 0.02
    amt = float(transaction.get("amount", 0.0))
    if amt > 500.0:
        score += 0.25
    if features.get("distinct_cards_per_device_24h", 1.0) > 2.0:
        score += 0.35
    if features.get("decline_rate_1h", 0.0) > 0.4:
        score += 0.30
    if features.get("amount_baseline_zscore", 0.0) > 2.5:
        score += 0.20
    return float(np.clip(score, 0.0, 0.98))


if __name__ == "__main__":
    sample_txn = {
        "transaction_id": "TXN-888001",
        "timestamp": "2026-01-20 15:30:00",
        "merchant": "fraud_Vandervort_Tech",
        "merchant_category": "shopping_net",
        "amount": 1450.00,
        "card_num": "4532_9999_1111",
        "device_id": "DEV_ATO_99",
        "declined": 0
    }
    res = score_transaction(sample_txn)
    print("Sample Scored Transaction:")
    print(json.dumps(res, indent=2))
