"""
simulate_live_stream.py - Live feed transaction simulator.

Replays processed/injected transactions through:
    scoring_service.py -> decision_engine.py -> explain_api.py -> db.py (SQLite)
at configurable time intervals to drive the live dashboard stream.
"""

import os
import sys
import time
import json
import pandas as pd
from typing import Optional

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.person_a.scoring_service import score_transaction
from src.person_b.decision_engine import evaluate_decision
from src.person_b.explain_api import explain_fraud_flag
from src.db import save_scored_transaction

INJECTED_CSV = os.path.join(_PROJECT_ROOT, "data", "processed", "injected_transactions.csv")


def process_single_event(raw_txn: dict, history_context: list = None) -> dict:
    """Process a single transaction end-to-end and persist to SQLite."""
    # Step 1: Real-time ML scoring + cohort baseline lookup
    scored = score_transaction(raw_txn, history_context)

    # Step 2: Decision Engine (Defense-only action mapping)
    decision = evaluate_decision(scored)

    # Step 3: Explainability Layer (Gemini API for non-allow actions)
    if decision["action"] != "allow":
        explanation = explain_fraud_flag(decision)
    else:
        explanation = "Transaction cleared automated risk boundary checks."

    decision["explanation"] = explanation

    # Step 4: Persist to SQLite Database
    save_scored_transaction(decision)
    return decision


def start_stream_simulation(interval_seconds: float = 1.0, max_events: Optional[int] = None):
    """Run stream simulation loop over dataset."""
    if not os.path.exists(INJECTED_CSV):
        print("[stream_sim] Injected transactions dataset missing. Running injection pipeline...")
        from src.person_a.inject_fraud_spikes import main as inject_main
        inject_main()

    df = pd.read_csv(INJECTED_CSV)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    print(f"[stream_sim] Starting live stream simulator ({len(df)} transactions available, interval={interval_seconds}s)...")

    recent_history = []
    processed_count = 0

    for idx, row in df.iterrows():
        txn = row.to_dict()

        # Execute end-to-end processing pipeline
        out = process_single_event(txn, recent_history)
        processed_count += 1

        # Keep rolling history window for velocity features (5000 rows ≈ full 24h across
        # all merchants, preventing context eviction for active merchant windows)
        recent_history.append(txn)
        if len(recent_history) > 5000:
            recent_history.pop(0)

        flag_str = f" [{out['action'].upper()}]" if out["action"] != "allow" else ""
        print(f"[stream_sim] Txn {out['transaction_id']}: ${out['amount']:,.2f} at {out['merchant']} -> Risk: {out['risk_score']:.2f}{flag_str}")

        if max_events and processed_count >= max_events:
            print(f"[stream_sim] Reached max events limit ({max_events}). Stopping stream.")
            break

        time.sleep(interval_seconds)


def main():
    start_stream_simulation(interval_seconds=0.8)


if __name__ == "__main__":
    main()
