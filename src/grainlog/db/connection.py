"""Database connection factory."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from grainlog.config import get_db_path
from grainlog.db.schema import initialize_schema


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Create a new SQLite connection with WAL mode and FK enforcement."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    initialize_schema(conn)
    return conn
