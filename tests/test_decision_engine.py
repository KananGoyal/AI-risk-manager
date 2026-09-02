import pytest
from src.person_b.decision_engine import evaluate_decision, DEFENSE_ACTIONS, load_threshold_config

def test_strictly_defense_only_actions():
    cfg = load_threshold_config()
    threshold = float(cfg.get("optimal_threshold", 0.35))

    scored_low = {"transaction_id": "TX-1", "risk_score": max(0.00, threshold - 0.02), "amount": 50.0}
    scored_high = {"transaction_id": "TX-2", "risk_score": 0.90, "amount": 1500.0}

    out_low = evaluate_decision(scored_low)
    out_high = evaluate_decision(scored_high)

    assert out_low["action"] in DEFENSE_ACTIONS
    assert out_high["action"] in DEFENSE_ACTIONS
    assert out_low["action"] == "allow"
    assert out_high["action"] == "auto_decline"

def test_decision_schema_output():
    scored = {
        "transaction_id": "TX-3",
        "risk_score": 0.55,
        "amount": 300.0,
        "merchant": "fraud_Kirlin_Inc",
        "merchant_category": "shopping_net"
    }
    out = evaluate_decision(scored)
    
    required_keys = [
        "transaction_id", "timestamp", "merchant", "merchant_category",
        "amount", "risk_score", "risk_band", "action", "cohort_context",
        "threshold_used", "estimated_fp_cost_at_threshold", "estimated_fraud_caught_at_threshold"
    ]
    for k in required_keys:
        assert k in out, f"Missing key in decision engine output: {k}"
