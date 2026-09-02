"""
threshold_analysis.py - Precision/Recall/False-Positive-Cost trade-off analysis across decision thresholds.

Derives cost-curve data on held-out evaluation set for:
1. Decision engine default threshold selection
2. Interactive frontend cost-curve threshold slider chart
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.person_a.feature_engineering import compute_features_batch, FEATURE_COLUMNS

MODELS_DIR = os.path.join(_PROJECT_ROOT, "data", "models")
PROCESSED_DIR = os.path.join(_PROJECT_ROOT, "data", "processed")
INJECTED_CSV = os.path.join(PROCESSED_DIR, "injected_transactions.csv")
MODEL_PATH = os.path.join(MODELS_DIR, "fraud_model.joblib")
THRESHOLD_JSON = os.path.join(MODELS_DIR, "threshold_analysis.json")


def analyze_thresholds():
    os.makedirs(MODELS_DIR, exist_ok=True)

    if not os.path.exists(MODEL_PATH) or not os.path.exists(INJECTED_CSV):
        print("[threshold_analysis] Model or dataset missing, running training script...")
        from src.person_a.train import train_model
        train_model()

    print(f"[threshold_analysis] Loading model from {MODEL_PATH}...")
    model = joblib.load(MODEL_PATH)

    print(f"[threshold_analysis] Loading dataset from {INJECTED_CSV}...")
    df = pd.read_csv(INJECTED_CSV)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    full_df = compute_features_batch(df)

    # Use held-out 20% for threshold analysis
    n_train = int(len(full_df) * 0.8)
    test_df = full_df.iloc[n_train:].copy()

    X_test = test_df[FEATURE_COLUMNS]
    y_test = test_df["is_fraud"].values
    amounts = test_df["amount"].values

    y_pred_prob = model.predict_proba(X_test)[:, 1]

    # Evaluate thresholds from 0.05 to 0.95 in steps of 0.05
    threshold_results = []
    avg_txn_amt = float(np.mean(amounts))

    for t in np.arange(0.05, 0.96, 0.05):
        t = round(float(t), 2)
        y_pred = (y_pred_prob >= t).astype(int)

        tp = np.sum((y_pred == 1) & (y_test == 1))
        fp = np.sum((y_pred == 1) & (y_test == 0))
        tn = np.sum((y_pred == 0) & (y_test == 0))
        fn = np.sum((y_pred == 0) & (y_test == 1))

        precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        # Cost estimation:
        # False Positive cost: blocked legitimate transaction revenue ($ value of FP transactions)
        fp_mask = (y_pred == 1) & (y_test == 0)
        fp_cost = float(np.sum(amounts[fp_mask]))

        # Fraud caught: monetary value of detected fraud
        tp_mask = (y_pred == 1) & (y_test == 1)
        fraud_caught = float(np.sum(amounts[tp_mask]))

        # False Negative cost: undetected fraud loss
        fn_mask = (y_pred == 0) & (y_test == 1)
        fn_cost = float(np.sum(amounts[fn_mask]))

        threshold_results.append({
            "threshold": t,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "tp_count": int(tp),
            "fp_count": int(fp),
            "fn_count": int(fn),
            "estimated_fp_cost": round(fp_cost, 2),
            "estimated_fraud_caught": round(fraud_caught, 2),
            "estimated_fn_cost": round(fn_cost, 2),
            "net_loss": round(fp_cost + fn_cost, 2)
        })

    # Find optimal threshold by minimum net loss / max F1
    best_item = max(threshold_results, key=lambda x: x["f1_score"])
    print(f"[threshold_analysis] Optimal Threshold derived: {best_item['threshold']} (F1={best_item['f1_score']}, Precision={best_item['precision']}, Recall={best_item['recall']})")

    output_payload = {
        "optimal_threshold": best_item["threshold"],
        "recommended_bands": {
            "low": {"max": best_item["threshold"], "action": "allow"},
            "medium": {"min": best_item["threshold"], "max": min(0.70, round(best_item["threshold"] + 0.20, 2)), "action": "flag_for_review"},
            "high": {"min": min(0.70, round(best_item["threshold"] + 0.20, 2)), "max": 0.85, "action": "hold_for_verification"},
            "very_high": {"min": 0.85, "max": 1.00, "action": "auto_decline"}
        },
        "threshold_curve": threshold_results
    }

    with open(THRESHOLD_JSON, "w") as f:
        json.dump(output_payload, f, indent=2)

    print(f"[threshold_analysis] Saved threshold curve report to {THRESHOLD_JSON}")
    return output_payload


def main():
    analyze_thresholds()


if __name__ == "__main__":
    main()
