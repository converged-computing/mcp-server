import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict

from .base import Database


class SqliteDatabase(Database):
    """
    Saves results into a SQLite table.
    URI Format: sqlite:///path/to/database.db
    """

    def __init__(self, uri: str):
        # Parse path from sqlite://path/to/db
        path = uri.replace("sqlite://", "")
        self.db_path = os.path.expanduser(os.path.expandvars(path))
        self.conn = None

    def connect(self):
        # Ensure dir exists
        directory = os.path.dirname(self.db_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        self.conn = sqlite3.connect(self.db_path)
        self._migrate()

    def _migrate(self):
        """Create table if not exists."""
        query = """
        CREATE TABLE IF NOT EXISTS workflow_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            status TEXT,
            plan_source TEXT,
            data JSON
        );
        """
        with self.conn:
            self.conn.execute(query)

    def save(self, data: Dict[str, Any]):
        if not self.conn:
            self.connect()

        timestamp = datetime.now().isoformat()
        status = data.get("status", "unknown")
        plan_source = data.get("plan_source", "unknown")
        json_data = json.dumps(data)

        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO workflow_runs (timestamp, status, plan_source, data) VALUES (?, ?, ?, ?)",
                    (timestamp, status, plan_source, json_data),
                )
            print(f"💾 Results saved to SQLite: {self.db_path} (ID: last_insert_rowid)")
        except Exception as e:
            print(f"❌ Failed to save results to SQLite: {e}")

    def close(self):
        if self.conn:
            self.conn.close()
