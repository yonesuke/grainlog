"""Shared test fixtures."""

from __future__ import annotations

import sqlite3

import pytest

from grainlog.db.schema import initialize_schema


@pytest.fixture
def conn():
    """Provide an in-memory SQLite connection with schema initialized."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    initialize_schema(c)
    yield c
    c.close()
