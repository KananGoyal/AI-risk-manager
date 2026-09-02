"""
db.py - SQLite persistence layer for AI Risk Manager (data/risk_manager.db).

Stores scored transactions, decision outputs, and Gemini explanations.
Supports concurrent thread-safe writes from stream simulator and reads from FastAPI server.
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
    conn.close()


def save_scored_transaction(record: Dict[str, Any]):
    """Insert or update a scored transaction record in SQLite."""
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


# Auto-initialize DB schema on import
init_db()
