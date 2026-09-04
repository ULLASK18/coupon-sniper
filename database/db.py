"""
SQLite database for accounts, coupons, and logs.
"""
from __future__ import annotations

import csv
import io
import os
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


DB_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(os.path.dirname(DB_DIR), "coupon_sniper.db")


@dataclass
class Account:
    id: Optional[int]
    username: str
    platform: str = "x"
    enabled: bool = True
    created_at: str = ""


@dataclass
class Coupon:
    id: Optional[int]
    code: str
    tweet_url: str = ""
    tweet_id: str = ""
    account: str = ""
    detected_at: str = ""
    status: str = "detected"


@dataclass
class LogEntry:
    id: Optional[int]
    level: str
    message: str
    timestamp: str = ""


class Database:
    """Thread-safe SQLite database manager."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._local = threading.local()
        self._init_db()

    @property
    def _conn(self) -> sqlite3.Connection:
        """One connection per thread for thread safety."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        conn = self._conn
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                platform TEXT NOT NULL DEFAULT 'x',
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS coupons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                tweet_url TEXT DEFAULT '',
                tweet_id TEXT DEFAULT '',
                account TEXT DEFAULT '',
                detected_at TEXT NOT NULL DEFAULT (datetime('now')),
                status TEXT DEFAULT 'detected'
            );

            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL DEFAULT 'INFO',
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS tweet_state (
                username TEXT PRIMARY KEY,
                last_seen_tweet_id TEXT NOT NULL DEFAULT ''
            );
        """)
        conn.commit()

    # ── Account CRUD ──────────────────────────────────────────────

    def add_account(self, username: str, platform: str = "x") -> bool:
        """Add a new account. Returns False if already exists."""
        username = username.lstrip("@").strip().lower()
        if not username:
            return False
        try:
            self._conn.execute(
                "INSERT INTO accounts (username, platform) VALUES (?, ?)",
                (username, platform),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def remove_account(self, username: str) -> None:
        username = username.lstrip("@").strip().lower()
        self._conn.execute("DELETE FROM accounts WHERE username = ?", (username,))
        self._conn.execute("DELETE FROM tweet_state WHERE username = ?", (username,))
        self._conn.commit()

    def get_accounts(self, enabled_only: bool = False) -> list[Account]:
        query = "SELECT * FROM accounts"
        if enabled_only:
            query += " WHERE enabled = 1"
        query += " ORDER BY created_at DESC"
        rows = self._conn.execute(query).fetchall()
        return [
            Account(
                id=r["id"],
                username=r["username"],
                platform=r["platform"],
                enabled=bool(r["enabled"]),
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def toggle_account(self, username: str, enabled: bool) -> None:
        username = username.lstrip("@").strip().lower()
        self._conn.execute(
            "UPDATE accounts SET enabled = ? WHERE username = ?",
            (int(enabled), username),
        )
        self._conn.commit()

    # ── Coupon CRUD ───────────────────────────────────────────────

    def is_duplicate_coupon(self, code: str) -> bool:
        row = self._conn.execute(
            "SELECT id FROM coupons WHERE code = ?", (code.upper(),)
        ).fetchone()
        return row is not None

    def save_coupon(
        self,
        code: str,
        tweet_url: str = "",
        tweet_id: str = "",
        account: str = "",
    ) -> bool:
        """Save coupon if not duplicate. Returns True if saved."""
        code_upper = code.upper()
        if self.is_duplicate_coupon(code_upper):
            return False
        self._conn.execute(
            "INSERT INTO coupons (code, tweet_url, tweet_id, account) VALUES (?, ?, ?, ?)",
            (code_upper, tweet_url, tweet_id, account),
        )
        self._conn.commit()
        return True

    def get_coupon_history(self, limit: int = 200, search: str = "") -> list[Coupon]:
        if search:
            rows = self._conn.execute(
                "SELECT * FROM coupons WHERE code LIKE ? OR account LIKE ? ORDER BY detected_at DESC LIMIT ?",
                (f"%{search}%", f"%{search}%", limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM coupons ORDER BY detected_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            Coupon(
                id=r["id"],
                code=r["code"],
                tweet_url=r["tweet_url"],
                tweet_id=r["tweet_id"],
                account=r["account"],
                detected_at=r["detected_at"],
                status=r["status"],
            )
            for r in rows
        ]

    def get_coupons_today_count(self) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        row = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM coupons WHERE detected_at LIKE ?",
            (f"{today}%",),
        ).fetchone()
        return row["cnt"] if row else 0

    def export_csv(self) -> str:
        """Export coupon history as CSV string."""
        coupons = self.get_coupon_history(limit=10000)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Code", "Account", "Tweet URL", "Tweet ID", "Detected At", "Status"])
        for c in coupons:
            writer.writerow([c.code, c.account, c.tweet_url, c.tweet_id, c.detected_at, c.status])
        return output.getvalue()

    # ── Tweet State ───────────────────────────────────────────────

    def get_last_seen_tweet_id(self, username: str) -> str:
        username = username.lstrip("@").strip().lower()
        row = self._conn.execute(
            "SELECT last_seen_tweet_id FROM tweet_state WHERE username = ?",
            (username,),
        ).fetchone()
        return row["last_seen_tweet_id"] if row else ""

    def set_last_seen_tweet_id(self, username: str, tweet_id: str) -> None:
        username = username.lstrip("@").strip().lower()
        self._conn.execute(
            "INSERT INTO tweet_state (username, last_seen_tweet_id) VALUES (?, ?) "
            "ON CONFLICT(username) DO UPDATE SET last_seen_tweet_id = ?",
            (username, tweet_id, tweet_id),
        )
        self._conn.commit()

    # ── Logs ──────────────────────────────────────────────────────

    def save_log(self, level: str, message: str) -> None:
        self._conn.execute(
            "INSERT INTO logs (level, message) VALUES (?, ?)",
            (level.upper(), message),
        )
        self._conn.commit()

    def get_recent_logs(self, limit: int = 100) -> list[LogEntry]:
        rows = self._conn.execute(
            "SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [
            LogEntry(
                id=r["id"],
                level=r["level"],
                message=r["message"],
                timestamp=r["timestamp"],
            )
            for r in reversed(rows)  # oldest first for display
        ]
