"""
Shared fixtures for Oracle Forge utility tests.
"""
import pytest
import pandas as pd
import tempfile
import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Join Key Resolver fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def df_postgres_customers():
    """Simulates a PostgreSQL customers table with integer customer_id."""
    return pd.DataFrame({
        "customer_id": [1001, 1002, 1003, 1004, 1005],
        "name": ["Alice", "Bob", "Carol", "Dave", "Eve"],
        "plan_type": ["enterprise", "starter", "enterprise", "starter", "pro"],
    })


@pytest.fixture
def df_duckdb_cust_prefix():
    """Simulates a DuckDB table with CUST-0001001 style keys."""
    return pd.DataFrame({
        "cid": ["CUST-0001001", "CUST-0001002", "CUST-0001003", "CUST-0001004", "CUST-0001005"],
        "churn_score": [0.82, 0.15, 0.71, 0.44, 0.91],
    })


@pytest.fixture
def df_sqlite_c_prefix():
    """Simulates a SQLite table with C{id} style keys."""
    return pd.DataFrame({
        "customer_ref": ["C1001", "C1002", "C1003", "C1004", "C1005"],
        "nps_score": [72, -30, 85, 10, -60],
    })


@pytest.fixture
def df_yelp_business():
    """Simulates a DuckDB Yelp business table with 22-char IDs."""
    return pd.DataFrame({
        "business_id": [
            "4JNXUYY8wbaaDmk3BPzlWw",
            "RESDUcs7fIiihp38-d6_6g",
            "K7lWdNUhCbcnEvI0NhGewg",
        ],
        "name": ["Pizza Palace", "Burger Barn", "Taco Town"],
        "stars": [4.5, 3.8, 4.1],
    })


@pytest.fixture
def df_mongo_reviews():
    """Simulates MongoDB reviews with matching 22-char business_id."""
    return pd.DataFrame({
        "business_id": [
            "4JNXUYY8wbaaDmk3BPzlWw",
            "RESDUcs7fIiihp38-d6_6g",
            "K7lWdNUhCbcnEvI0NhGewg",
        ],
        "review_count": [120, 45, 89],
        "avg_stars": [4.6, 3.7, 4.0],
    })


# ---------------------------------------------------------------------------
# Corrections log fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_corrections_log(tmp_path):
    """Creates a temporary corrections_log.md with sample entries."""
    content = """# Corrections Log

---

**Dataset**: crmarenapro | **Query**: q3
**Query**: How many customers have a churn score above 0.7?
**What went wrong**: Direct JOIN on customer_id (int) vs cid (CUST-0001001 string) produced 0 rows.
**Correct approach**: Strip CUST- prefix and leading zeros: `df['cid_int'] = df['cid'].str.replace(r'^CUST-0*', '', regex=True).astype(int)` then merge on integer key.

---

**Dataset**: yelp | **Query**: q5
**Query**: Which state has the most businesses offering free WiFi?
**What went wrong**: MongoDB WiFi attribute stored as Python repr string "u'free'" not plain "free". Filter `{"attributes.WiFi": "free"}` returns 0 documents.
**Correct approach**: Use regex filter or fetch all and filter in Python: `[b for b in businesses if 'free' in str(b.get('attributes', {}).get('WiFi', '')).lower()]`

---

**Dataset**: yelp | **Query**: q3
**Query**: How many reviews mention wait time as a complaint?
**What went wrong**: SQL LIKE '%wait%' over-counts by 300% including positive "worth the wait" mentions.
**Correct approach**: Use regex in execute_python to match only negative wait patterns: `re.compile(r'long wait|waited (too long|forever)', re.I)`

---
"""
    log_file = tmp_path / "corrections_log.md"
    log_file.write_text(content, encoding="utf-8")
    return log_file
