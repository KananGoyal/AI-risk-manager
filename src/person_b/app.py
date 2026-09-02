# src/person_b/app.py
# Streamlit Internal Debug Dashboard for AI Risk Manager (Fraud-Spike Detector)

import sys
import os
import time
import json
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.person_a.scoring_service import score_transaction
from src.person_b.decision_engine import evaluate_decision
from src.person_b.explain_api import explain_fraud_flag
from src.db import get_live_transactions

st.set_page_config(
    page_title="AI Risk Manager - Internal Debug Dashboard",
    page_icon="🛡️",
    layout="wide",
)

st.markdown("## 🛡️ AI Risk Manager — Internal Pipeline Debugger")
st.caption("Internal debug interface for Person A / Person B pipeline validation.")

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.subheader("Simulate Single Transaction")
    with st.form("debug_txn_form"):
        merchant = st.selectbox(
            "Merchant Name",
            [
                "fraud_Vandervort_Tech",
                "fraud_Cruickshank_Apparel",
                "fraud_Kirlin_Inc",
                "fraud_Baumbach_Stores",
                "fraud_Rippin_LLC"
            ]
        )
        category = st.selectbox("Category", ["shopping_net", "grocery_pos", "entertainment", "travel"])
        amount = st.number_input("Amount ($)", min_value=1.0, max_value=50000.0, value=1450.0, step=50.0)
        card_num = st.text_input("Card Number", "4532_9999_1111")
        device_id = st.text_input("Device ID", "DEV_DEBUG_01")
        declined = st.checkbox("Was Declined Previously", value=False)
        submit_btn = st.form_submit_button("⚡ Score & Evaluate")

if submit_btn:
    txn = {
        "transaction_id": f"TXN-DEBUG-{int(time.time()*1000)%100000:05d}",
        "timestamp": pd.Timestamp.now(),
        "merchant": merchant,
        "merchant_category": category,
        "amount": amount,
        "card_num": card_num,
        "device_id": device_id,
        "declined": 1 if declined else 0
    }

    t0 = time.perf_counter()
    scored = score_transaction(txn)
    decision = evaluate_decision(scored)
    if decision["action"] != "allow":
        explanation = explain_fraud_flag(decision)
    else:
        explanation = "Transaction cleared automated risk boundary checks."
    elapsed = (time.perf_counter() - t0) * 1000.0

    with col_right:
        st.subheader("Pipeline Evaluation Output")
        st.success(f"Scored & Evaluated in {elapsed:.2f} ms")

        st.metric("Fraud Risk Score", f"{decision['risk_score']:.2%}")
        st.metric("Defense Action", decision["action"].upper())
        st.metric("Risk Band", decision["risk_band"].upper())

        st.markdown("**Gemini Audit Reason:**")
        st.info(explanation)

        st.markdown("**Structured Decision Output JSON:**")
        st.json(decision)

with st.expander("Recent SQLite Persistence Records"):
    txns = get_live_transactions(limit=10)
    st.write(f"Total SQLite rows retrieved: {len(txns)}")
    if txns:
        st.dataframe(pd.DataFrame(txns))
