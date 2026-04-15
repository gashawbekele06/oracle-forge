"""
Oracle Forge — MCP Server
==========================
Exposes Oracle Forge's database tools and natural language query capability
as a Model Context Protocol (MCP) server.

Compatible with:
  - Claude Desktop (via stdio transport)
  - Cursor, Zed, and any MCP-compatible client
  - Docker (via SSE transport on port 8000)

Tools exposed:
  1. oracle_ask          — natural language question → answer (full agent run)
  2. oracle_query_db     — raw SQL or MongoDB query against any dataset DB
  3. oracle_list_db      — list tables or collections in a dataset DB
  4. oracle_datasets     — list all available DAB datasets
  5. oracle_schema       — get database schema for a dataset

Architecture:
  - Tools 2-4 call DataAgentBench's QueryDBTool and ListDBTool directly
    (fast, no LLM call needed)
  - Tool 1 runs the full OracleAgent pipeline (LLM required, 20s–5min)
  - All tools resolve database connections via db_config.yaml per dataset

Reference: https://github.com/googleapis/genai-toolbox (Google MCP Toolbox pattern)
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

# ── Path setup ────────────────────────────────────────────────────────────────
_MCP_DIR = Path(__file__).parent
_APP_ROOT = _MCP_DIR.parent
_DAB_ROOT = Path(os.getenv("DAB_ROOT", str(_APP_ROOT / "DataAgentBench")))
_KB_ROOT = Path(os.getenv("KB_ROOT", str(_APP_ROOT / "kb")))
_AGENT_DIR = _APP_ROOT / "agent"

for p in [str(_APP_ROOT), str(_DAB_ROOT), str(_AGENT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from mcp.server.fastmcp import FastMCP  # type: ignore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("oracle-forge-mcp")

# ── FastMCP server ────────────────────────────────────────────────────────────
mcp = FastMCP(
    "Oracle Forge",
    instructions=(
        "Oracle Forge is a multi-database analytics agent. "
        "Use oracle_datasets to discover available datasets, "
        "oracle_schema to understand the database structure, "
        "oracle_query_db for raw queries, and oracle_ask for "
        "complex natural language analytics questions."
    ),
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_dataset_dir(dataset: str) -> Path:
    """Find the DataAgentBench query directory for a dataset."""
    for name in [dataset, dataset.upper(), dataset.lower()]:
        d = _DAB_ROOT / f"query_{name}"
        if d.exists():
            return d
    raise ValueError(
        f"Dataset '{dataset}' not found. "
        f"Run oracle_datasets to see available datasets."
    )


def _load_db_config(dataset: str) -> dict:
    """Load db_config.yaml for a dataset."""
    import yaml  # type: ignore
    dataset_dir = _resolve_dataset_dir(dataset)
    config_path = dataset_dir / "db_config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"db_config.yaml not found for dataset '{dataset}'")
    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    # DAB configs have a top-level 'db_clients' key or are flat
    return raw.get("db_clients", raw) if isinstance(raw, dict) else {}


def _available_datasets() -> list[str]:
    """Return all dataset names present in DataAgentBench."""
    if not _DAB_ROOT.exists():
        return []
    return sorted(
        d.name.replace("query_", "")
        for d in _DAB_ROOT.iterdir()
        if d.is_dir() and d.name.startswith("query_") and (d / "db_config.yaml").exists()
    )


def _run_sql_query(db_cfg: dict, sql: str) -> list[dict]:
    """Execute SQL against PostgreSQL, SQLite, or DuckDB."""
    db_type = db_cfg.get("db_type", "")

    if db_type == "postgres":
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(
            host=os.getenv("PG_HOST", db_cfg.get("host", "localhost")),
            port=int(os.getenv("PG_PORT", db_cfg.get("port", 5432))),
            user=os.getenv("PG_USER", db_cfg.get("user", "postgres")),
            password=os.getenv("PG_PASSWORD", db_cfg.get("password", "")),
            dbname=db_cfg.get("db_name", "postgres"),
        )
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql)
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return rows

    elif db_type == "sqlite":
        import sqlite3
        db_path = db_cfg.get("db_path") or db_cfg.get("path", "")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(sql)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    elif db_type == "duckdb":
        import duckdb
        db_path = db_cfg.get("db_path") or db_cfg.get("path", "")
        conn = duckdb.connect(db_path, read_only=True)
        result = conn.execute(sql).fetchdf()
        conn.close()
        return result.to_dict(orient="records")

    raise ValueError(f"Unsupported db_type '{db_type}' for SQL query")


def _run_mongo_query(db_cfg: dict, query_str: str) -> list[dict]:
    """Execute a MongoDB query (JSON string) against a collection."""
    from pymongo import MongoClient
    mongo_uri = os.getenv("MONGO_URI", db_cfg.get("uri", "mongodb://localhost:27017/"))
    client = MongoClient(mongo_uri)
    db = client[db_cfg.get("db_name", "")]

    # Parse query: {"collection": "...", "filter": {...}, "limit": 100}
    try:
        q = json.loads(query_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid MongoDB query JSON: {e}")

    collection = q.get("collection") or q.get("col")
    if not collection:
        raise ValueError("MongoDB query must include 'collection' key. E.g.: {\"collection\": \"reviews\", \"filter\": {}}")

    pipeline = q.get("pipeline")
    if pipeline:
        docs = list(db[collection].aggregate(pipeline))
    else:
        filt = q.get("filter", {})
        proj = q.get("projection")
        limit = int(q.get("limit", 100))
        cursor = db[collection].find(filt, proj).limit(limit)
        docs = list(cursor)

    client.close()
    # Remove ObjectId (not JSON serialisable)
    for doc in docs:
        doc.pop("_id", None)
    return docs


# ── Tool 1: oracle_ask ────────────────────────────────────────────────────────

@mcp.tool()
def oracle_ask(question: str, dataset: str, llm: str = "gpt-4o") -> str:
    """
    Ask a natural language analytics question about a dataset.

    Runs the full Oracle Forge agent pipeline:
    schema injection → LLM planning → multi-DB queries → self-correction → answer.

    Args:
        question: Natural language question (e.g. "Which state has the most 5-star restaurants?")
        dataset:  DAB dataset name (e.g. "yelp", "crmarenapro", "stockmarket").
                  Use oracle_datasets to see all available datasets.
        llm:      LLM to use. Options: "gpt-4o", "claude-opus-4-6", "claude-sonnet-4-6".
                  Defaults to gpt-4o.

    Returns:
        Plain-text answer with supporting context.

    Note: This tool makes LLM API calls and may take 20 seconds to 5 minutes.
    """
    logger.info(f"oracle_ask: dataset={dataset} llm={llm} question={question[:80]}...")

    try:
        _resolve_dataset_dir(dataset)
    except ValueError as e:
        return f"Error: {e}"

    # Find the closest matching query in the dataset by asking a one-shot question
    # We use query_id=1 as the entry point and override the question
    try:
        from oracle_agent import OracleAgent  # type: ignore

        # We need a query_id but this is a freeform question
        # Create a temporary query.json so DataAgent can load it
        import tempfile, shutil, yaml

        dataset_dir = _resolve_dataset_dir(dataset)
        tmp_query_dir = Path(tempfile.mkdtemp()) / "query_mcp"
        tmp_query_dir.mkdir(parents=True)

        # Copy db_config and db_description from the real dataset
        shutil.copy(dataset_dir / "db_config.yaml", tmp_query_dir.parent / "db_config.yaml")
        for fname in ["db_description.txt", "db_description_withhint.txt"]:
            src = dataset_dir / fname
            if src.exists():
                shutil.copy(src, tmp_query_dir.parent / fname)

        # Write the freeform question as query.json
        query_json = {
            "question": question,
            "dataset": dataset,
            "query_id": "mcp",
        }
        (tmp_query_dir / "query.json").write_text(json.dumps(query_json), encoding="utf-8")

        # Run DataAgent directly (bypass OracleAgent's query_dir resolution)
        import yaml as yaml_lib
        from common_scaffold.DataAgent import DataAgent  # type: ignore
        from context_manager import ContextManager  # type: ignore

        ctx = ContextManager(kb_root=_KB_ROOT, dab_root=_DAB_ROOT)
        db_description = (dataset_dir / "db_description_withhint.txt").read_text(encoding="utf-8") \
            if (dataset_dir / "db_description_withhint.txt").exists() \
            else (dataset_dir / "db_description.txt").read_text(encoding="utf-8") \
            if (dataset_dir / "db_description.txt").exists() else ""
        db_description += "\n\n" + ctx.build(dataset=dataset, use_hints=False)

        agent = DataAgent(
            query_dir=tmp_query_dir,
            db_description=db_description,
            db_config_path=str(dataset_dir / "db_config.yaml"),
            deployment_name=llm,
            exec_python_timeout=300,
            max_iterations=50,
            root_name="mcp_ask",
        )
        # Override the question
        agent.messages[0]["content"] = agent.messages[0]["content"].replace(
            agent.query, question
        ) if hasattr(agent, "query") else agent.messages[0]["content"]

        answer = agent.run()
        shutil.rmtree(tmp_query_dir.parent, ignore_errors=True)
        return answer or "The agent could not produce an answer. Try rephrasing the question."

    except Exception as e:
        logger.exception("oracle_ask failed")
        return f"Agent error: {type(e).__name__}: {e}"


# ── Tool 2: oracle_query_db ───────────────────────────────────────────────────

@mcp.tool()
def oracle_query_db(dataset: str, db_name: str, query: str) -> str:
    """
    Run a raw SQL or MongoDB query against a dataset database.

    For SQL databases (PostgreSQL, SQLite, DuckDB): pass a SQL SELECT statement.
    For MongoDB: pass a JSON object with keys:
      - "collection": collection name (required)
      - "filter": MongoDB filter dict (optional, default {})
      - "projection": fields to include/exclude (optional)
      - "limit": max documents to return (optional, default 100)
      - "pipeline": aggregation pipeline array (optional, overrides filter)

    Args:
        dataset: DAB dataset name (e.g. "yelp", "crmarenapro")
        db_name: Logical database name from db_config.yaml (e.g. "yelp_db", "yelp_mongo")
        query:   SQL SELECT statement or MongoDB JSON query

    Returns:
        JSON array of result rows/documents, or error message.

    Example SQL:
        oracle_query_db("yelp", "yelp_db", "SELECT name, stars FROM business LIMIT 5")

    Example MongoDB:
        oracle_query_db("yelp", "yelp_mongo", '{"collection": "reviews", "filter": {"stars": 5}, "limit": 10}')
    """
    logger.info(f"oracle_query_db: dataset={dataset} db={db_name}")

    try:
        db_configs = _load_db_config(dataset)
    except (ValueError, FileNotFoundError) as e:
        return f"Error: {e}"

    if db_name not in db_configs:
        available = list(db_configs.keys())
        return f"Database '{db_name}' not found in dataset '{dataset}'. Available: {available}"

    cfg = db_configs[db_name]
    db_type = cfg.get("db_type", "unknown")

    try:
        if db_type == "mongo":
            rows = _run_mongo_query(cfg, query)
        else:
            rows = _run_sql_query(cfg, query)

        if not rows:
            return "Query returned 0 rows."

        # Truncate large results
        truncated = len(rows) > 200
        display_rows = rows[:200]
        result = json.dumps(display_rows, default=str, indent=2)
        if truncated:
            result += f"\n\n... (showing first 200 of {len(rows)} rows)"
        return result

    except Exception as e:
        logger.exception("oracle_query_db failed")
        return f"Query error ({db_type}): {type(e).__name__}: {e}"


# ── Tool 3: oracle_list_db ────────────────────────────────────────────────────

@mcp.tool()
def oracle_list_db(dataset: str, db_name: str) -> str:
    """
    List tables (SQL) or collections (MongoDB) in a dataset database.

    Args:
        dataset: DAB dataset name (e.g. "yelp")
        db_name: Logical database name from db_config.yaml

    Returns:
        Formatted list of tables/collections with row/document counts.
    """
    logger.info(f"oracle_list_db: dataset={dataset} db={db_name}")

    try:
        db_configs = _load_db_config(dataset)
    except (ValueError, FileNotFoundError) as e:
        return f"Error: {e}"

    if db_name not in db_configs:
        available = list(db_configs.keys())
        return f"Database '{db_name}' not found. Available: {available}"

    cfg = db_configs[db_name]
    db_type = cfg.get("db_type", "unknown")
    lines = [f"Database: {db_name} (type: {db_type})"]

    try:
        if db_type == "postgres":
            rows = _run_sql_query(cfg, """
                SELECT table_name,
                       pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) AS size
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            for r in rows:
                try:
                    count_rows = _run_sql_query(cfg, f"SELECT COUNT(*) as n FROM \"{r['table_name']}\"")
                    n = count_rows[0]["n"] if count_rows else "?"
                except Exception:
                    n = "?"
                lines.append(f"  TABLE {r['table_name']} — {n:,} rows ({r.get('size', '?')})")

        elif db_type == "sqlite":
            rows = _run_sql_query(cfg, "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            for r in rows:
                try:
                    count_rows = _run_sql_query(cfg, f"SELECT COUNT(*) as n FROM \"{r['name']}\"")
                    n = count_rows[0]["n"] if count_rows else "?"
                except Exception:
                    n = "?"
                lines.append(f"  TABLE {r['name']} — {n:,} rows")

        elif db_type == "duckdb":
            rows = _run_sql_query(cfg,
                "SELECT table_name FROM information_schema.tables WHERE table_schema='main' ORDER BY table_name")
            for r in rows:
                tname = r.get("table_name", "")
                try:
                    count_rows = _run_sql_query(cfg, f'SELECT COUNT(*) as n FROM "{tname}"')
                    n = count_rows[0]["n"] if count_rows else "?"
                except Exception:
                    n = "?"
                lines.append(f"  TABLE {tname} — {n:,} rows")

        elif db_type == "mongo":
            from pymongo import MongoClient
            mongo_uri = os.getenv("MONGO_URI", cfg.get("uri", "mongodb://localhost:27017/"))
            client = MongoClient(mongo_uri)
            db = client[cfg.get("db_name", "")]
            for coll_name in sorted(db.list_collection_names()):
                n = db[coll_name].estimated_document_count()
                lines.append(f"  COLLECTION {coll_name} — {n:,} documents")
            client.close()

        else:
            lines.append(f"  (Cannot list — unsupported db_type: {db_type})")

    except Exception as e:
        lines.append(f"  Error listing: {type(e).__name__}: {e}")

    return "\n".join(lines)


# ── Tool 4: oracle_datasets ───────────────────────────────────────────────────

@mcp.tool()
def oracle_datasets() -> str:
    """
    List all available DataAgentBench datasets with their database types.

    Returns:
        Formatted list of datasets, their databases, and DB types.
        Use the dataset name with oracle_ask, oracle_query_db, oracle_list_db.
    """
    datasets = _available_datasets()
    if not datasets:
        return (
            "No datasets found. Make sure DataAgentBench is mounted at "
            f"{_DAB_ROOT} with dataset directories (query_yelp/, query_crmarenapro/, etc.)"
        )

    lines = [f"Available datasets ({len(datasets)} total):\n"]
    for ds in datasets:
        try:
            db_configs = _load_db_config(ds)
            db_list = ", ".join(
                f"{name} ({cfg.get('db_type', '?')})"
                for name, cfg in db_configs.items()
            )
        except Exception:
            db_list = "(config error)"
        lines.append(f"  {ds:<22} → {db_list}")

    lines.append("\nUsage example:")
    lines.append('  oracle_ask("Which state has the most 5-star restaurants?", "yelp")')
    lines.append('  oracle_query_db("yelp", "yelp_db", "SELECT state, COUNT(*) FROM business GROUP BY state")')
    return "\n".join(lines)


# ── Tool 5: oracle_schema ─────────────────────────────────────────────────────

@mcp.tool()
def oracle_schema(dataset: str) -> str:
    """
    Get the full database schema description for a dataset.

    Returns the DataAgentBench db_description.txt (with hints if available),
    which includes table structures, column types, and join key guidance.

    Args:
        dataset: DAB dataset name (e.g. "yelp", "crmarenapro", "PATENTS")

    Returns:
        Full schema description text used by the Oracle Forge agent.
    """
    try:
        dataset_dir = _resolve_dataset_dir(dataset)
    except ValueError as e:
        return f"Error: {e}"

    # Prefer the hints version
    for fname in ["db_description_withhint.txt", "db_description.txt"]:
        path = dataset_dir / fname
        if path.exists():
            content = path.read_text(encoding="utf-8").strip()
            return f"Schema for dataset '{dataset}' ({fname}):\n\n{content}"

    return f"No schema description found for dataset '{dataset}'"


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Oracle Forge MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport: 'stdio' for Claude Desktop, 'sse' for Docker/HTTP (default: stdio)",
    )
    parser.add_argument("--port", type=int, default=8000, help="Port for SSE transport (default: 8000)")
    args = parser.parse_args()

    if args.transport == "sse":
        logger.info(f"Starting Oracle Forge MCP server (SSE) on port {args.port}...")
        mcp.run(transport="sse", port=args.port)
    else:
        logger.info("Starting Oracle Forge MCP server (stdio)...")
        mcp.run(transport="stdio")
