"""
train.py - Train XGBoost/GradientBoosted fraud detection classifier with time-based split.

Actions:
1. Loads injected transactions dataset.
2. Computes rolling window features via feature_engineering.py.
3. Performs time-based 80/20 train/held-out split.
4. Fits XGBoost / HistGradientBoosting classifier.
5. Precomputes & exports merchant cohort baseline statistics to data/models/merchant_baselines.json.
6. Exports model artifact to data/models/fraud_model.joblib.
7. Saves evaluation report (Precision, Recall, PR-AUC, ROC-AUC) to data/models/evaluation_report.json.
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
from sklearn.metrics import precision_score, recall_score, precision_recall_curve, auc, roc_auc_score

MODELS_DIR = os.path.join(_PROJECT_ROOT, "data", "models")
PROCESSED_DIR = os.path.join(_PROJECT_ROOT, "data", "processed")
INJECTED_CSV = os.path.join(PROCESSED_DIR, "injected_transactions.csv")
MODEL_PATH = os.path.join(MODELS_DIR, "fraud_model.joblib")
BASELINES_PATH = os.path.join(MODELS_DIR, "merchant_baselines.json")
REPORT_PATH = os.path.join(MODELS_DIR, "evaluation_report.json")
THRESHOLD_JSON = os.path.join(MODELS_DIR, "threshold_analysis.json")

# Documented fallback default threshold if threshold_analysis.json is not yet generated
DEFAULT_THRESHOLD = 0.35


def train_model():
    os.makedirs(MODELS_DIR, exist_ok=True)

    if not os.path.exists(INJECTED_CSV):
        print(f"[train] Injected dataset missing at {INJECTED_CSV}. Running injection pipeline...")
        from src.person_a.inject_fraud_spikes import main as inject_main
        inject_main()

    print(f"[train] Loading injected dataset from {INJECTED_CSV}...")
    df = pd.read_csv(INJECTED_CSV)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Feature calculation
    full_df = compute_features_batch(df)

    # Time-based split: Train on first 80%, Evaluate on last 20%
    n_total = len(full_df)
    n_train = int(n_total * 0.8)

    train_df = full_df.iloc[:n_train]
    test_df = full_df.iloc[n_train:]

    print(f"[train] Time-based split: {len(train_df)} train txns ({train_df['timestamp'].min()} to {train_df['timestamp'].max()})")
    print(f"[train]                     {len(test_df)} held-out txns ({test_df['timestamp'].min()} to {test_df['timestamp'].max()})")

    X_train = train_df[FEATURE_COLUMNS]
    y_train = train_df["is_fraud"]
    X_test = test_df[FEATURE_COLUMNS]
    y_test = test_df["is_fraud"]

    print(f"[train] Train fraud label ratio: {y_train.mean():.2%}")
    print(f"[train] Test fraud label ratio:  {y_test.mean():.2%}")

    # Compute class imbalance weight for minority fraud class
    n_neg = int((y_train == 0).sum())
    n_pos = int((y_train == 1).sum())
    spw = n_neg / max(n_pos, 1)
    print(f"[train] scale_pos_weight: {spw:.2f} (neg={n_neg}, pos={n_pos})")

    # Model training with XGBoost or HistGradientBoosting fallback
    try:
        from xgboost import XGBClassifier
        print("[train] Training XGBoost classifier...")
        model = XGBClassifier(
            n_estimators=120,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.85,
            colsample_bytree=0.85,
            scale_pos_weight=spw,
            random_state=42,
            eval_metric="logloss"
        )
        model.fit(X_train, y_train)
    except ImportError:
        print("[train] XGBoost not found, using Scikit-Learn HistGradientBoostingClassifier fallback...")
        from sklearn.ensemble import HistGradientBoostingClassifier
        model = HistGradientBoostingClassifier(
            max_iter=120,
            max_depth=6,
            learning_rate=0.08,
            random_state=42
        )
        model.fit(X_train, y_train)

    # Load cost-optimal threshold from threshold_analysis.json if available
    eval_threshold = DEFAULT_THRESHOLD
    if os.path.exists(THRESHOLD_JSON):
        try:
            with open(THRESHOLD_JSON, "r") as f:
                t_data = json.load(f)
                eval_threshold = float(t_data.get("optimal_threshold", DEFAULT_THRESHOLD))
                print(f"[train] Loaded cost-optimal threshold from {THRESHOLD_JSON}: {eval_threshold}")
        except Exception as e:
            print(f"[train] Warning reading {THRESHOLD_JSON}: {e}. Using fallback default threshold {DEFAULT_THRESHOLD}")
    else:
        print(f"[train] {THRESHOLD_JSON} not found. Using fallback default threshold {DEFAULT_THRESHOLD}")

    # Evaluation on held-out split using cost-optimal threshold
    y_pred_prob = model.predict_proba(X_test)[:, 1]
    y_pred_binary = (y_pred_prob >= eval_threshold).astype(int)

    precision = float(precision_score(y_test, y_pred_binary, zero_division=0))
    recall = float(recall_score(y_test, y_pred_binary, zero_division=0))
    roc_auc = float(roc_auc_score(y_test, y_pred_prob))

    prec_array, rec_array, _ = precision_recall_curve(y_test, y_pred_prob)
    pr_auc = float(auc(rec_array, prec_array))

    print(f"[train] Held-Out Evaluation Results (Threshold={eval_threshold}):")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  PR-AUC:    {pr_auc:.4f}")
    print(f"  ROC-AUC:   {roc_auc:.4f}")

    # Save model artifact
    joblib.dump(model, MODEL_PATH)
    print(f"[train] Saved model artifact to {MODEL_PATH}")

    # Compute and export merchant/category cohort baselines
    print("[train] Precomputing cohort baselines for instant real-time lookup...")
    merchant_baselines = {}
    grouped = full_df.groupby("merchant")
    for merchant_name, m_group in grouped:
        merchant_baselines[merchant_name] = {
            "mean_amount": float(m_group["amount"].mean()),
            "std_amount": float(m_group["amount"].std() if len(m_group) > 1 else 15.0),
            "txn_count_24h_avg": float(len(m_group) / 30.0),
            "category": m_group["merchant_category"].iloc[0],
            "fraud_rate": float(m_group["is_fraud"].mean())
        }

    # Add default global baseline
    merchant_baselines["__GLOBAL_DEFAULT__"] = {
        "mean_amount": float(full_df["amount"].mean()),
        "std_amount": float(full_df["amount"].std()),
        "txn_count_24h_avg": float(len(full_df) / (30.0 * 12.0)),
        "category": "grocery_pos",
        "fraud_rate": float(full_df["is_fraud"].mean())
    }

    with open(BASELINES_PATH, "w") as f:
        json.dump(merchant_baselines, f, indent=2)
    print(f"[train] Saved merchant baselines to {BASELINES_PATH}")

    # Save evaluation report
    report = {
        "model_type": type(model).__name__,
        "train_samples": int(len(X_train)),
        "held_out_samples": int(len(X_test)),
        "held_out_time_range": {
            "start": str(test_df["timestamp"].min()),
            "end": str(test_df["timestamp"].max())
        },
        "evaluation_metrics": {
            "threshold_used": eval_threshold,
            "precision": precision,
            "recall": recall,
            "pr_auc": pr_auc,
            "roc_auc": roc_auc
        },
        "feature_names": FEATURE_COLUMNS
    }

    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print(f"[train] Saved evaluation report to {REPORT_PATH}")

    return model, report


def main():
    train_model()


if __name__ == "__main__":
    main()
