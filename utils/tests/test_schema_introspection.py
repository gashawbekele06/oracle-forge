"""Tests for utils/schema_introspection.py (unit tests — no live DB required)"""

import sys
from pathlib import Path
import pytest
import tempfile
import yaml
import os

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.schema_introspection import SchemaInspector


SAMPLE_CONFIG = {
    "yelp_db": {
        "db_type": "duckdb",
        "db_path": "/nonexistent/yelp.duckdb",
    },
    "yelp_mongo": {
        "db_type": "mongo",
        "uri": "mongodb://localhost:27017/",
        "db_name": "yelp",
    },
}


def test_schema_inspector_loads_config():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        yaml.dump(SAMPLE_CONFIG, f)
        tmp_path = f.name

    try:
        inspector = SchemaInspector(tmp_path)
        assert "yelp_db" in inspector.config
        assert "yelp_mongo" in inspector.config
    finally:
        os.unlink(tmp_path)


def test_schema_inspector_handles_missing_db_gracefully():
    """When DB is not reachable, describe_all should return error strings, not raise."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        yaml.dump(SAMPLE_CONFIG, f)
        tmp_path = f.name

    try:
        inspector = SchemaInspector(tmp_path)
        # Should not raise — gracefully handles connection errors
        result = inspector.describe_all()
        assert isinstance(result, str)
        # Should mention both DBs even if they fail
        assert "yelp_db" in result or "Failed" in result
    finally:
        os.unlink(tmp_path)


def test_schema_inspector_sqlite_in_memory():
    """Test SQLite introspection with an in-memory database file."""
    import sqlite3
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        # Create a test database
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT);")
        conn.execute("INSERT INTO users VALUES (1, 'Alice', 'alice@example.com');")
        conn.execute("INSERT INTO users VALUES (2, 'Bob', 'bob@example.com');")
        conn.commit()
        conn.close()

        config = {"test_sqlite": {"db_type": "sqlite", "db_path": db_path}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            inspector = SchemaInspector(config_path)
            result = inspector.describe_all()
            assert "users" in result
            assert "2 rows" in result
            assert "name" in result
        finally:
            os.unlink(config_path)
    finally:
        os.unlink(db_path)
