"""
Oracle Forge — Schema Introspection Tool
==========================================
Provides schema introspection across all four DAB database types:
PostgreSQL, MongoDB, SQLite, DuckDB.

Used by the agent to discover table structure before querying
when the KB domain knowledge is incomplete.

Usage:
    from utils.schema_introspection import SchemaInspector

    inspector = SchemaInspector(db_config_path="query_yelp/db_config.yaml")
    schema = inspector.describe_all()
    print(schema)
"""

from __future__ import annotations

import json
import os
import yaml
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# SchemaInspector
# ---------------------------------------------------------------------------

class SchemaInspector:
    """
    Provides natural-language schema descriptions for all databases
    defined in a DAB db_config.yaml file.
    """

    def __init__(self, db_config_path: str | Path):
        self.db_config_path = Path(db_config_path)
        with open(self.db_config_path, encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    def describe_all(self) -> str:
        """Return a human-readable schema description for all databases."""
        parts: list[str] = []
        for db_name, db_cfg in self.config.items():
            try:
                desc = self._describe_db(db_name, db_cfg)
                parts.append(desc)
            except Exception as e:
                parts.append(f"[{db_name}]: Failed to introspect — {e}")
        return "\n\n".join(parts)

    def _describe_db(self, db_name: str, cfg: dict) -> str:
        db_type = cfg.get("db_type", "unknown")
        if db_type == "postgres":
            return self._describe_postgres(db_name, cfg)
        elif db_type == "mongo":
            return self._describe_mongo(db_name, cfg)
        elif db_type == "sqlite":
            return self._describe_sqlite(db_name, cfg)
        elif db_type == "duckdb":
            return self._describe_duckdb(db_name, cfg)
        return f"[{db_name}] Unknown db_type: {db_type}"

    # ── PostgreSQL ────────────────────────────────────────────────────
    def _describe_postgres(self, db_name: str, cfg: dict) -> str:
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=os.getenv("PG_HOST", cfg.get("host", "localhost")),
                port=int(os.getenv("PG_PORT", cfg.get("port", 5432))),
                user=os.getenv("PG_USER", cfg.get("user", "postgres")),
                password=os.getenv("PG_PASSWORD", cfg.get("password", "")),
                dbname=cfg.get("db_name", "postgres"),
            )
            cur = conn.cursor()

            # Get tables
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            tables = [row[0] for row in cur.fetchall()]

            lines = [f"[{db_name}] PostgreSQL — database: {cfg.get('db_name')}"]
            for table in tables:
                cur.execute(f"""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = %s AND table_schema = 'public'
                    ORDER BY ordinal_position;
                """, (table,))
                cols = cur.fetchall()
                cur.execute(f'SELECT COUNT(*) FROM "{table}";')
                row_count = cur.fetchone()[0]
                col_str = ", ".join(f"{c[0]} ({c[1]})" for c in cols)
                lines.append(f"  TABLE {table} ({row_count:,} rows): {col_str}")

            cur.close()
            conn.close()
            return "\n".join(lines)
        except Exception as e:
            return f"[{db_name}] PostgreSQL introspection failed: {e}"

    # ── MongoDB ────────────────────────────────────────────────────────
    def _describe_mongo(self, db_name: str, cfg: dict) -> str:
        try:
            from pymongo import MongoClient
            uri = os.getenv("MONGO_URI", cfg.get("uri", "mongodb://localhost:27017/"))
            client = MongoClient(uri)
            db = client[cfg.get("db_name", db_name)]

            lines = [f"[{db_name}] MongoDB — database: {cfg.get('db_name')}"]
            for coll_name in sorted(db.list_collection_names()):
                coll = db[coll_name]
                count = coll.estimated_document_count()
                sample = coll.find_one()
                if sample:
                    sample.pop("_id", None)
                    fields = list(sample.keys())[:10]
                    field_str = ", ".join(fields)
                    if len(sample) > 10:
                        field_str += f" ... (+{len(sample)-10} more)"
                else:
                    field_str = "(empty)"
                lines.append(f"  COLLECTION {coll_name} ({count:,} docs): {field_str}")

            client.close()
            return "\n".join(lines)
        except Exception as e:
            return f"[{db_name}] MongoDB introspection failed: {e}"

    # ── SQLite ─────────────────────────────────────────────────────────
    def _describe_sqlite(self, db_name: str, cfg: dict) -> str:
        try:
            import sqlite3
            db_path = cfg.get("db_path") or cfg.get("path")
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()

            cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            tables = [row[0] for row in cur.fetchall()]

            lines = [f"[{db_name}] SQLite — file: {db_path}"]
            for table in tables:
                cur.execute(f"PRAGMA table_info('{table}');")
                cols = [(row[1], row[2]) for row in cur.fetchall()]
                cur.execute(f'SELECT COUNT(*) FROM "{table}";')
                row_count = cur.fetchone()[0]
                col_str = ", ".join(f"{c[0]} ({c[1]})" for c in cols)
                lines.append(f"  TABLE {table} ({row_count:,} rows): {col_str}")

            conn.close()
            return "\n".join(lines)
        except Exception as e:
            return f"[{db_name}] SQLite introspection failed: {e}"

    # ── DuckDB ─────────────────────────────────────────────────────────
    def _describe_duckdb(self, db_name: str, cfg: dict) -> str:
        try:
            import duckdb
            db_path = cfg.get("db_path") or cfg.get("path")
            conn = duckdb.connect(db_path, read_only=True)

            tables = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main';"
            ).fetchall()

            lines = [f"[{db_name}] DuckDB — file: {db_path}"]
            for (table,) in tables:
                cols = conn.execute(f"DESCRIBE {table};").fetchall()
                row_count = conn.execute(f'SELECT COUNT(*) FROM "{table}";').fetchone()[0]
                col_str = ", ".join(f"{c[0]} ({c[1]})" for c in cols)
                lines.append(f"  TABLE {table} ({row_count:,} rows): {col_str}")

            conn.close()
            return "\n".join(lines)
        except Exception as e:
            return f"[{db_name}] DuckDB introspection failed: {e}"
