import pytest
import pandas as pd
from src.person_a.scoring_service import score_transaction
from src.person_b.decision_engine import evaluate_decision, DEFENSE_ACTIONS
from src.person_b.explain_api import explain_fraud_flag
from src.db import save_scored_transaction, get_transaction_by_id

def test_full_transaction_risk_chain():
    # Step 1: Input transaction
    raw_txn = {
        "transaction_id": "TXN-CHAIN-999",
        "timestamp": "2026-01-20 18:30:00",
        "merchant": "fraud_Vandervort_Tech",
        "merchant_category": "shopping_net",
        "amount": 1650.0,
        "card_num": "4532_8888_9999",
        "device_id": "DEV_CHAIN_01",
        "declined": 0
    }

    # Step 2: Scoring Service (ML + Cohort)
    scored = score_transaction(raw_txn)
    assert "risk_score" in scored
    assert 0.0 <= scored["risk_score"] <= 1.0
    assert "cohort_context" in scored

    # Step 3: Decision Engine
    decision = evaluate_decision(scored)
    assert decision["action"] in DEFENSE_ACTIONS
    assert decision["risk_band"] in ["low", "medium", "high", "very_high"]

    # Step 4: Explainability API
    explanation = explain_fraud_flag(decision)
    assert isinstance(explanation, str)
    assert len(explanation) > 10
    decision["explanation"] = explanation

    # Step 5: SQLite Persistence
    save_scored_transaction(decision)
    retrieved = get_transaction_by_id("TXN-CHAIN-999")
    assert retrieved is not None
    assert retrieved["transaction_id"] == "TXN-CHAIN-999"
    assert retrieved["explanation"] == explanation
