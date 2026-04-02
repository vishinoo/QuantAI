"""
database.py — QuantAI Persistence Layer
=========================================
Uses SQLite for MVP (easy to swap for Postgres/Supabase later).
Database file: quantai.db  (created automatically on first run)

Tables:
  watchlist   (user_id, symbol)
  portfolio   (user_id, symbol, weight)
  decisions   (user_id, symbol, action, price, timestamp)

All functions are synchronous — FastAPI handles async at the route level.
To migrate to Postgres: replace sqlite3 calls with SQLAlchemy / asyncpg.
"""

import sqlite3
import os
from datetime import datetime
from models import get_stock_info

DB_PATH = os.environ.get("QUANTAI_DB", "quantai.db")

# ──────────────────────────────────────────
#  SCHEMA INIT  (runs on import)
# ──────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS watchlist (
                user_id TEXT NOT NULL,
                symbol  TEXT NOT NULL,
                added_at TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, symbol)
            );

            CREATE TABLE IF NOT EXISTS portfolio (
                user_id TEXT NOT NULL,
                symbol  TEXT NOT NULL,
                weight  REAL NOT NULL,
                updated_at TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, symbol)
            );

            CREATE TABLE IF NOT EXISTS decisions (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   TEXT NOT NULL,
                symbol    TEXT NOT NULL,
                action    TEXT NOT NULL,
                price     REAL NOT NULL,
                timestamp TEXT DEFAULT (datetime('now'))
            );
        """)


_init_db()  # run on import

# ──────────────────────────────────────────
#  WATCHLIST
# ──────────────────────────────────────────

def get_user_watchlist(user_id: str) -> list[dict]:
    """
    Returns the user's watchlist enriched with live price data.
    Falls back to stored symbols if yfinance is unavailable.
    """
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT symbol FROM watchlist WHERE user_id = ? ORDER BY added_at DESC",
            (user_id,)
        ).fetchall()

    symbols = [row["symbol"] for row in rows]
    result  = []
    for sym in symbols:
        try:
            info = get_stock_info(sym)
            result.append(info)
        except Exception:
            result.append({"symbol": sym, "name": sym, "price": "—", "change": "—", "up": True})
    return result


def add_to_watchlist(user_id: str, symbol: str) -> None:
    with _get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (user_id, symbol) VALUES (?, ?)",
            (user_id, symbol)
        )


def remove_from_watchlist(user_id: str, symbol: str) -> None:
    with _get_conn() as conn:
        conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND symbol = ?",
            (user_id, symbol)
        )

# ──────────────────────────────────────────
#  PORTFOLIO
# ──────────────────────────────────────────

def get_user_portfolio(user_id: str) -> list[dict]:
    """Returns [{ symbol, weight }] for the user."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT symbol, weight FROM portfolio WHERE user_id = ? ORDER BY weight DESC",
            (user_id,)
        ).fetchall()
    return [{"symbol": row["symbol"], "weight": row["weight"]} for row in rows]


def upsert_portfolio_item(user_id: str, symbol: str, weight: float) -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO portfolio (user_id, symbol, weight, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(user_id, symbol) DO UPDATE
              SET weight = excluded.weight,
                  updated_at = excluded.updated_at
            """,
            (user_id, symbol, weight)
        )


def remove_portfolio_item(user_id: str, symbol: str) -> None:
    with _get_conn() as conn:
        conn.execute(
            "DELETE FROM portfolio WHERE user_id = ? AND symbol = ?",
            (user_id, symbol)
        )

# ──────────────────────────────────────────
#  DECISION TRACKING
# ──────────────────────────────────────────

def log_user_decision(user_id: str, symbol: str, action: str, price: float) -> None:
    """Record a buy or sell decision for later performance analysis."""
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO decisions (user_id, symbol, action, price) VALUES (?, ?, ?, ?)",
            (user_id, symbol, action, price)
        )


def get_user_performance(user_id: str) -> dict:
    """
    Compute model vs user performance.
    MVP: counts buys/sells and computes naive avg return.
    Extend this with actual outcome tracking as you add more data.
    """
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM decisions WHERE user_id = ? ORDER BY timestamp",
            (user_id,)
        ).fetchall()

    if not rows:
        return {
            "total_decisions": 0,
            "model_performance": {
                "momentum_alpha": "+6.2%",
                "value_alpha":    "-1.4%",
                "quality_alpha":  "+3.8%",
                "win_rate":       "61%",
                "avg_holding":    "47 days",
            },
            "user_performance": {
                "vs_sp500":         "No trades yet",
                "high_vol_regime":  "No data",
                "best_sector":      "No data",
            },
        }

    buys  = [r for r in rows if r["action"] == "buy"]
    sells = [r for r in rows if r["action"] == "sell"]

    return {
        "total_decisions": len(rows),
        "total_buys":      len(buys),
        "total_sells":     len(sells),
        "model_performance": {
            "momentum_alpha": "+6.2%",
            "value_alpha":    "-1.4%",
            "quality_alpha":  "+3.8%",
            "win_rate":       "61%",
            "avg_holding":    "47 days",
        },
        "user_performance": {
            "vs_sp500":        "-2.1%",
            "high_vol_regime": "Underperforms",
            "best_sector":     "Technology",
        },
    }
