"""
SQLite-backed memory store.

Tables:
  commands   — every user command + plan
  executions — every tool call + result
  preferences — learned key-value facts about the user
"""

from __future__ import annotations
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from config import MEMORY_DB_PATH


class MemoryStore:
    def __init__(self, db_path: str = MEMORY_DB_PATH):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS commands (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL    NOT NULL,
                    user_input TEXT   NOT NULL,
                    plan      TEXT,
                    success   INTEGER DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS executions (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    command_id INTEGER REFERENCES commands(id),
                    timestamp  REAL    NOT NULL,
                    tool_name  TEXT    NOT NULL,
                    args       TEXT,
                    status     TEXT,
                    result     TEXT
                );

                CREATE TABLE IF NOT EXISTS preferences (
                    key        TEXT PRIMARY KEY,
                    value      TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
            """)

    # ── Commands ──────────────────────────────────────────────────────────────

    def log_command(self, user_input: str, plan: list[dict] | None = None) -> int:
        """Log a user command and return its row ID."""
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO commands (timestamp, user_input, plan) VALUES (?, ?, ?)",
                (time.time(), user_input, json.dumps(plan) if plan else None),
            )
            return cur.lastrowid

    def update_command_status(self, command_id: int, success: bool):
        with self._connect() as conn:
            conn.execute(
                "UPDATE commands SET success = ? WHERE id = ?",
                (1 if success else 0, command_id),
            )

    def get_recent_commands(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM commands ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Executions ────────────────────────────────────────────────────────────

    def log_execution(
        self,
        command_id: int,
        tool_name: str,
        args: dict,
        status: str,
        result: Any,
    ):
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO executions
                   (command_id, timestamp, tool_name, args, status, result)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    command_id,
                    time.time(),
                    tool_name,
                    json.dumps(args),
                    status,
                    json.dumps(result),
                ),
            )

    def get_recent_executions(self, limit: int = 50) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM executions ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Preferences ───────────────────────────────────────────────────────────

    def set_preference(self, key: str, value: Any):
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO preferences (key, value, updated_at) VALUES (?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
                (key, json.dumps(value), time.time()),
            )

    def get_preference(self, key: str, default: Any = None) -> Any:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM preferences WHERE key = ?", (key,)
            ).fetchone()
        if row:
            return json.loads(row["value"])
        return default

    def get_all_preferences(self) -> dict[str, Any]:
        with self._connect() as conn:
            rows = conn.execute("SELECT key, value FROM preferences").fetchall()
        return {r["key"]: json.loads(r["value"]) for r in rows}

    # ── Habit inference ───────────────────────────────────────────────────────

    def get_frequent_apps(self, top_n: int = 5) -> list[str]:
        """Return the most frequently opened apps across all past commands."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT args, COUNT(*) as cnt
                   FROM executions
                   WHERE tool_name = 'open_app'
                   GROUP BY args
                   ORDER BY cnt DESC
                   LIMIT ?""",
                (top_n,),
            ).fetchall()
        apps = []
        for r in rows:
            try:
                args = json.loads(r["args"])
                apps.append(args.get("name", ""))
            except Exception:
                pass
        return [a for a in apps if a]

    def get_command_history_summary(self, limit: int = 10) -> str:
        """Return a readable summary of recent commands for context injection."""
        commands = self.get_recent_commands(limit)
        if not commands:
            return "No previous commands."
        lines = []
        for cmd in reversed(commands):
            status = "✓" if cmd["success"] else "✗"
            lines.append(f"  {status} {cmd['user_input']}")
        return "\n".join(lines)
