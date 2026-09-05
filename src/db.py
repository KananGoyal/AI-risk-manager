"""
db.py - SQLite persistence layer for AI Risk Manager (data/risk_manager.db).

Stores scored transactions, decision outputs, and Gemini explanations.
Supports concurrent thread-safe writes from stream simulator and reads from FastAPI server.

Also maintains a lightweight `transaction_history` table used by scoring_service.py
to hydrate rolling-window features (merchant velocity, decline rate, card/device diversity)
for real-time live scoring when no caller-provided history_context is available.
"""

import os
import sys
import json
import sqlite3
from typing import List, Dict, Any, Optional

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

DB_PATH = os.path.join(_PROJECT_ROOT, "data", "risk_manager.db")


def get_db_connection() -> sqlite3.Connection:
    """Open SQLite connection in WAL mode for concurrent performance."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db():
    """Create database tables if they do not exist."""
    conn = get_db_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scored_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE NOT NULL,
                timestamp TEXT NOT NULL,
                merchant TEXT NOT NULL,
                merchant_category TEXT NOT NULL,
                amount REAL NOT NULL,
                card_num TEXT,
                device_id TEXT,
                risk_score REAL NOT NULL,
                risk_band TEXT NOT NULL,
                action TEXT NOT NULL,
                cohort_context TEXT,
                top_features TEXT,
                explanation TEXT,
                threshold_used REAL,
                estimated_fp_cost REAL,
                estimated_fraud_caught REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_txn_id ON scored_transactions(transaction_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_action ON scored_transactions(action);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON scored_transactions(created_at);")

        # Lightweight table for real-time history hydration used by scoring_service.py.
        # Stores the minimal raw fields that compute_features() needs from history_context.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transaction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE NOT NULL,
                timestamp TEXT NOT NULL,
                merchant TEXT NOT NULL,
                merchant_category TEXT NOT NULL,
                amount REAL NOT NULL,
                card_num TEXT DEFAULT '',
                device_id TEXT DEFAULT '',
                declined INTEGER DEFAULT 0
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hist_merchant ON transaction_history(merchant);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hist_ts ON transaction_history(timestamp);")
    conn.close()


def save_scored_transaction(record: Dict[str, Any]):
    """Insert or update a scored transaction record in SQLite.
    Also writes the minimal raw fields to transaction_history so that
    future calls to get_recent_history_for_scoring() see this transaction.
    """
    conn = get_db_connection()
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO scored_transactions (
                transaction_id, timestamp, merchant, merchant_category, amount,
                card_num, device_id, risk_score, risk_band, action,
                cohort_context, top_features, explanation, threshold_used,
                estimated_fp_cost, estimated_fraud_caught
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            record["transaction_id"],
            str(record.get("timestamp")),
            record.get("merchant", "unknown"),
            record.get("merchant_category", "grocery_pos"),
            float(record.get("amount", 0.0)),
            record.get("card_num", ""),
            record.get("device_id", ""),
            float(record.get("risk_score", 0.0)),
            record.get("risk_band", "low"),
            record.get("action", "allow"),
            json.dumps(record.get("cohort_context", {})),
            json.dumps(record.get("top_features", {})),
            record.get("explanation", ""),
            float(record.get("threshold_used", 0.35)),
            float(record.get("estimated_fp_cost", 0.0)),
            float(record.get("estimated_fraud_caught", 0.0)),
        ))

        # Infer 'declined' from action: auto_decline = definitely declined.
        action = record.get("action", "allow")
        declined_flag = 1 if action == "auto_decline" else 0
        conn.execute("""
            INSERT OR IGNORE INTO transaction_history (
                transaction_id, timestamp, merchant, merchant_category,
                amount, card_num, device_id, declined
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            record["transaction_id"],
            str(record.get("timestamp")),
            record.get("merchant", "unknown"),
            record.get("merchant_category", "grocery_pos"),
            float(record.get("amount", 0.0)),
            record.get("card_num", ""),
            record.get("device_id", ""),
            declined_flag,
        ))
    conn.close()


def get_live_transactions(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve recent scored transactions ordered by id DESC."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM scored_transactions
        ORDER BY id DESC
        LIMIT ?;
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        item = dict(r)
        if item.get("cohort_context"):
            try:
                item["cohort_context"] = json.loads(item["cohort_context"])
            except Exception:
                pass
        if item.get("top_features"):
            try:
                item["top_features"] = json.loads(item["top_features"])
            except Exception:
                pass
        result.append(item)
    return result


def get_transaction_by_id(tx_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve details for a single transaction."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scored_transactions WHERE transaction_id = ? LIMIT 1;", (tx_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None
    item = dict(row)
    if item.get("cohort_context"):
        try:
            item["cohort_context"] = json.loads(item["cohort_context"])
        except Exception:
            pass
    if item.get("top_features"):
        try:
            item["top_features"] = json.loads(item["top_features"])
        except Exception:
            pass
    return item


def load_history_from_csv(csv_path: str) -> int:
    """Bulk-load the full processed/injected transaction CSV into transaction_history.

    Idempotent: skips rows already present (INSERT OR IGNORE on transaction_id).
    Returns the count of newly inserted rows.
    """
    import pandas as pd

    if not os.path.exists(csv_path):
        print(f"[db] load_history_from_csv: file not found at {csv_path} — skipping.")
        return 0

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM transaction_history;")
    existing = cursor.fetchone()[0]
    conn.close()

    df = pd.read_csv(csv_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"]).astype(str)

    # Normalise required columns; fill missing with safe defaults
    for col, default in [("card_num", ""), ("device_id", ""), ("declined", 0)]:
        if col not in df.columns:
            df[col] = default
    df["declined"] = df["declined"].fillna(0).astype(int)

    if "transaction_id" not in df.columns:
        df["transaction_id"] = [f"HIST-{i:07d}" for i in range(len(df))]

    rows = df[["transaction_id", "timestamp", "merchant", "merchant_category",
               "amount", "card_num", "device_id", "declined"]].values.tolist()

    conn = get_db_connection()
    with conn:
        conn.executemany("""
            INSERT OR IGNORE INTO transaction_history (
                transaction_id, timestamp, merchant, merchant_category,
                amount, card_num, device_id, declined
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, rows)
    conn.close()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM transaction_history;")
    new_total = cursor.fetchone()[0]
    conn.close()

    inserted = new_total - existing
    print(f"[db] load_history_from_csv: loaded {inserted} new rows into transaction_history "
          f"(total={new_total}, file={os.path.basename(csv_path)})")
    return inserted


def get_recent_history_for_scoring(
    merchant: str,
    lookback_hours: int = 24,
    reference_timestamp=None,
) -> List[Dict[str, Any]]:
    """Fetch the last `lookback_hours` of raw transaction history for a merchant.

    Args:
        merchant:            Merchant identifier to filter on.
        lookback_hours:      How many hours back from reference_timestamp to look.
        reference_timestamp: Anchor point for the lookback window.  Can be a
                             datetime, ISO-8601 string, or pandas Timestamp.
                             Defaults to UTC now (correct for live scoring).
                             Pass the transaction's own timestamp when replaying
                             historical data so the window anchors to the
                             simulation time rather than wall-clock time.

    Returns a list of dicts with keys matching what compute_features() expects:
        timestamp, merchant, merchant_category, amount, card_num, device_id, declined

    Falls back to an empty list if no history is available (brand-new merchant).
    """
    from datetime import datetime, timedelta, timezone

    if reference_timestamp is None:
        anchor = datetime.now(timezone.utc)
    else:
        # Accept datetime, pd.Timestamp, or ISO string
        if hasattr(reference_timestamp, "to_pydatetime"):
            anchor = reference_timestamp.to_pydatetime()
        elif isinstance(reference_timestamp, str):
            anchor = datetime.fromisoformat(reference_timestamp.replace("Z", "+00:00"))
        else:
            anchor = reference_timestamp
        # Make timezone-aware if naive
        if anchor.tzinfo is None:
            anchor = anchor.replace(tzinfo=timezone.utc)

    cutoff = (anchor - timedelta(hours=lookback_hours)).isoformat()
    anchor_str = anchor.isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, merchant, merchant_category, amount, card_num, device_id, declined
        FROM   transaction_history
        WHERE  merchant = ?
          AND  timestamp >= ?
          AND  timestamp <  ?
        ORDER  BY timestamp ASC;
    """, (merchant, cutoff, anchor_str))
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "timestamp":          r["timestamp"],
            "merchant":           r["merchant"],
            "merchant_category":  r["merchant_category"],
            "amount":             float(r["amount"]),
            "card_num":           r["card_num"] or "",
            "device_id":          r["device_id"] or "",
            "declined":           int(r["declined"]),
        }
        for r in rows
    ]


# Auto-initialize DB schema on import
init_db()
