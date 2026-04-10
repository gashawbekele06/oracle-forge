"""Tests for utils/join_key_resolver.py"""

import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.join_key_resolver import (
    detect_format,
    resolve_join,
    JoinKeyResolver,
    strip_cust_prefix,
    strip_c_prefix,
    int_to_str,
)


# ---------------------------------------------------------------------------
# detect_format
# ---------------------------------------------------------------------------

def test_detect_cust_prefix():
    s = pd.Series(["CUST-0001001", "CUST-0000042", "CUST-0123456"])
    assert detect_format(s) == "cust_prefix"


def test_detect_c_prefix():
    s = pd.Series(["C1001", "C42", "C123456"])
    assert detect_format(s) == "c_prefix"


def test_detect_integer():
    s = pd.Series([1001, 42, 123456])
    assert detect_format(s) == "integer"


def test_detect_integer_string():
    s = pd.Series(["1001", "42", "123456"])
    assert detect_format(s) == "integer"


def test_detect_yelp_id():
    s = pd.Series(["iCQpiavjjPzJ5_3gPD5Eq", "Ha3iJu77CxlrFm-vQRs_8g"])
    assert detect_format(s) == "yelp_id"


def test_detect_unknown():
    s = pd.Series(["mixed-format-1", "different_2", "abc123"])
    assert detect_format(s) == "unknown"


# ---------------------------------------------------------------------------
# Normalizers
# ---------------------------------------------------------------------------

def test_strip_cust_prefix():
    s = pd.Series(["CUST-0001001", "CUST-0000042", "CUST-0000001"])
    result = strip_cust_prefix(s)
    assert list(result) == ["1001", "42", "1"]


def test_strip_c_prefix():
    s = pd.Series(["C1001", "C42", "C1"])
    result = strip_c_prefix(s)
    assert list(result) == ["1001", "42", "1"]


def test_int_to_str():
    s = pd.Series([1001, 42, 1])
    result = int_to_str(s)
    assert list(result) == ["1001", "42", "1"]


# ---------------------------------------------------------------------------
# resolve_join (cross-DB merge)
# ---------------------------------------------------------------------------

def test_resolve_join_cust_prefix_to_integer():
    """Merge PostgreSQL int IDs with DuckDB CUST- prefixed IDs."""
    df_pg = pd.DataFrame({
        "customer_id": [1001, 42, 999],
        "name": ["Alice", "Bob", "Charlie"],
    })
    df_duck = pd.DataFrame({
        "cid": ["CUST-0001001", "CUST-0000042", "CUST-0000999"],
        "ticket_count": [3, 1, 5],
    })

    merged = resolve_join(df_pg, "customer_id", df_duck, "cid")

    assert len(merged) == 3
    assert set(merged["name"]) == {"Alice", "Bob", "Charlie"}
    assert set(merged["ticket_count"]) == {3, 1, 5}


def test_resolve_join_c_prefix_to_integer():
    """Merge int IDs with C-prefixed IDs."""
    df_a = pd.DataFrame({"id": [100, 200, 300], "value": ["x", "y", "z"]})
    df_b = pd.DataFrame({"ref": ["C100", "C200", "C300"], "score": [0.9, 0.5, 0.1]})

    merged = resolve_join(df_a, "id", df_b, "ref")
    assert len(merged) == 3


def test_resolve_join_no_mismatch():
    """Direct string match — should still work."""
    df_a = pd.DataFrame({"bid": ["abc123456789012345678901", "xyz123456789012345678901"], "cat": ["A", "B"]})
    df_b = pd.DataFrame({"bid": ["abc123456789012345678901", "xyz123456789012345678901"], "val": [1, 2]})

    merged = resolve_join(df_a, "bid", df_b, "bid")
    assert len(merged) == 2


def test_resolve_join_no_match_returns_empty():
    """No matching IDs → empty DataFrame."""
    df_a = pd.DataFrame({"id": [1, 2, 3], "v": ["a", "b", "c"]})
    df_b = pd.DataFrame({"id": [4, 5, 6], "w": ["d", "e", "f"]})

    merged = resolve_join(df_a, "id", df_b, "id")
    assert len(merged) == 0


# ---------------------------------------------------------------------------
# JoinKeyResolver describe()
# ---------------------------------------------------------------------------

def test_resolver_describe():
    df_a = pd.DataFrame({"customer_id": [1, 2, 3]})
    df_b = pd.DataFrame({"cid": ["CUST-0000001", "CUST-0000002", "CUST-0000003"]})

    resolver = JoinKeyResolver(df_a, "customer_id", df_b, "cid")
    desc = resolver.describe()
    assert "integer" in desc
    assert "cust_prefix" in desc
