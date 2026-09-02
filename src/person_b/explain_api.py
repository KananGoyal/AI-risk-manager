"""
explain_api.py - Generative AI Fraud-Flag Explanation Layer using Gemini API.

Input: Decision engine structured output (score, band, action, cohort context, top features).
Output: 1-2 plain-language sentences explaining flag reasons for merchant operations.
Trigger: Only called when action != "allow".
Caching: In-memory & SQLite cache keyed by transaction_id.
"""

import os
import sys
import json
import time
from typing import Dict, Any
from dotenv import load_dotenv

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

# In-memory explanation cache keyed by transaction_id
_EXPLANATION_CACHE: Dict[str, str] = {}
MODEL_NAME = "gemini-2.5-flash-lite"


def _get_genai_client():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        from google.genai import types
        return genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(
                    attempts=3,
                    initial_delay=1.5,
                    max_delay=10.0,
                    http_status_codes=[429, 500, 502, 503, 504]
                )
            )
        )
    except Exception as e:
        print(f"[explain_api] Gemini client init warning: {e}")
        return None


def explain_fraud_flag(decision_output: Dict[str, Any]) -> str:
    """Generate or retrieve a cached 1-2 sentence plain-language fraud explanation."""
    tx_id = decision_output.get("transaction_id", "UNKNOWN")
    action = decision_output.get("action", "allow")

    # Trigger condition: Only explain flagged/held/declined transactions
    if action == "allow":
        return "Transaction cleared standard automated risk checks."

    # Return cached explanation if present
    if tx_id in _EXPLANATION_CACHE:
        return _EXPLANATION_CACHE[tx_id]

    score = decision_output.get("risk_score", 0.0)
    band = decision_output.get("risk_band", "medium")
    merchant = decision_output.get("merchant", "Merchant")
    amount = decision_output.get("amount", 0.0)
    cohort = decision_output.get("cohort_context", {})
    top_features = decision_output.get("top_features", {})

    mean_amt = cohort.get("historical_mean_amount", 65.0)
    ratio = cohort.get("amount_ratio_vs_baseline", round(amount / max(mean_amt, 1.0), 1))
    z_score = cohort.get("baseline_zscore", top_features.get("amount_baseline_zscore", 0.0))

    client = _get_genai_client()

    if client:
        prompt = (
            "You are a payment fraud risk analyst for a payment gateway. "
            "Write exactly 1-2 plain-language sentences explaining why the following transaction was flagged. "
            "Focus on specific numerical deviations (e.g. amount vs historical baseline, device velocity) "
            "so merchant ops can understand the decision without data science jargon.\n\n"
            f"Transaction ID: {tx_id}\n"
            f"Merchant: {merchant} ({decision_output.get('merchant_category', 'general')})\n"
            f"Amount: ${amount:,.2f} (Historical merchant baseline average: ${mean_amt:,.2f}, {ratio}x baseline)\n"
            f"Risk Score: {score:.2f} (Band: {band}, Action: {action})\n"
            f"Baseline Z-Score: {z_score:.2f}\n"
            f"Top Feature Signals: {json.dumps(top_features)}\n"
        )
        try:
            response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
            if response and response.text:
                explanation = response.text.strip()
                _EXPLANATION_CACHE[tx_id] = explanation
                return explanation
        except Exception as e:
            print(f"[explain_api] Gemini API call error: {e}")

    # Deterministic heuristic fallback explanation
    explanation = (
        f"Flagged ({action.upper()}): Transaction of ${amount:,.2f} at {merchant} is {ratio}x "
        f"above the merchant's historical baseline (${mean_amt:,.2f}), presenting an elevated risk score of {score:.2f} "
        f"with a baseline z-score deviation of {z_score:.1f}."
    )
    _EXPLANATION_CACHE[tx_id] = explanation
    return explanation


if __name__ == "__main__":
    sample_decision = {
        "transaction_id": "TXN-888999",
        "action": "hold_for_verification",
        "risk_score": 0.82,
        "risk_band": "high",
        "merchant": "fraud_Vandervort_Tech",
        "merchant_category": "shopping_net",
        "amount": 1450.00,
        "cohort_context": {
            "historical_mean_amount": 65.0,
            "amount_ratio_vs_baseline": 22.3,
            "baseline_zscore": 4.1
        },
        "top_features": {
            "amount_baseline_zscore": 4.1,
            "distinct_cards_per_device_24h": 3.0
        }
    }
    exp = explain_fraud_flag(sample_decision)
    print("Generated Fraud Explanation:")
    print(exp)
