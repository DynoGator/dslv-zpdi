"""
Lightweight WAL-mode SQLite cache for latest state.
Used by the web server to fetch the most recent telemetry.
"""
import os
import sqlite3
import time
from pathlib import Path

class SQLiteCache:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path_str = os.environ.get("ZPDI_SQLITE_PATH", "./data/zpdi_cache.db")
            path = Path(path_str)
        self._path = path
        self._conn = None

    def open(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS latest_state ("
            "  id INTEGER PRIMARY KEY CHECK (id = 1),"
            "  wall_ns INTEGER,"
            "  payload TEXT"
            ")"
        )
        self._conn.commit()

    def update(self, payload_json: str, wall_ns: int | None = None) -> None:
        if not self._conn:
            return
        if wall_ns is None:
            wall_ns = int(time.time() * 1e9)
        try:
            self._conn.execute(
                "INSERT INTO latest_state (id, wall_ns, payload) VALUES (1, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET wall_ns=excluded.wall_ns, payload=excluded.payload",
                (wall_ns, payload_json),
            )
            self._conn.commit()
        except Exception:
            pass

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
