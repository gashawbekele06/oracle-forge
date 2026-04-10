"""
Oracle Forge — Join Key Resolver
==================================
Utility for detecting and resolving join key format mismatches
across heterogeneous databases (the #2 DAB hard requirement).

Usage:
    from utils.join_key_resolver import JoinKeyResolver, resolve_join

    # Auto-detect and normalize
    df_pg['cid_norm'] = JoinKeyResolver.normalize(df_pg['customer_id'], source='postgres')
    df_duck['cid_norm'] = JoinKeyResolver.normalize(df_duck['cid'], source='duckdb_crmarenapro')
    merged = pd.merge(df_pg, df_duck, on='cid_norm')
"""

from __future__ import annotations

import re
import pandas as pd
from typing import Callable


# ---------------------------------------------------------------------------
# Known format registry
# ---------------------------------------------------------------------------

# Maps (dataset, db_type) → (column_patterns, normalizer_function)
# Each normalizer takes a pd.Series and returns a pd.Series of str keys

_NORMALIZERS: dict[str, Callable[[pd.Series], pd.Series]] = {}


def _register(name: str):
    def decorator(fn: Callable[[pd.Series], pd.Series]):
        _NORMALIZERS[name] = fn
        return fn
    return decorator


@_register("strip_cust_prefix")
def strip_cust_prefix(series: pd.Series) -> pd.Series:
    """'CUST-0001001' → '1001'"""
    return (
        series.astype(str)
        .str.replace(r"^CUST-0*", "", regex=True)
        .str.strip()
    )


@_register("strip_c_prefix")
def strip_c_prefix(series: pd.Series) -> pd.Series:
    """'C1001' → '1001'"""
    return (
        series.astype(str)
        .str.replace(r"^C0*", "", regex=True)
        .str.strip()
    )


@_register("int_to_str")
def int_to_str(series: pd.Series) -> pd.Series:
    """1001 (int) → '1001' (str, no leading zeros)"""
    return series.apply(lambda x: str(int(x)) if pd.notnull(x) else "").astype(str)


@_register("objectid_to_str")
def objectid_to_str(series: pd.Series) -> pd.Series:
    """MongoDB ObjectId → 24-char hex string"""
    return series.astype(str).str.strip()


@_register("identity")
def identity(series: pd.Series) -> pd.Series:
    """No transformation needed."""
    return series.astype(str).str.strip()


# ---------------------------------------------------------------------------
# Auto-detection
# ---------------------------------------------------------------------------

def detect_format(series: pd.Series) -> str:
    """
    Detect the join key format in a series.
    Returns one of: 'cust_prefix', 'c_prefix', 'integer', 'uuid', 'yelp_id', 'unknown'
    """
    sample = series.dropna().astype(str).head(20)
    if sample.empty:
        return "unknown"

    if sample.str.match(r"^CUST-\d+$").all():
        return "cust_prefix"
    if sample.str.match(r"^C\d+$").all():
        return "c_prefix"
    if sample.str.match(r"^\d+$").all():
        return "integer"
    if sample.str.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$").all():
        return "uuid"
    if sample.str.match(r"^[A-Za-z0-9_-]{22}$").all():
        return "yelp_id"  # Yelp business/user IDs are 22-char alphanumeric
    if sample.str.match(r"^[0-9a-f]{24}$").all():
        return "mongo_objectid"

    return "unknown"


def get_normalizer(fmt: str) -> Callable[[pd.Series], pd.Series]:
    """Return the normalizer function for a detected format."""
    return {
        "cust_prefix": _NORMALIZERS["strip_cust_prefix"],
        "c_prefix": _NORMALIZERS["strip_c_prefix"],
        "integer": _NORMALIZERS["int_to_str"],
        "uuid": _NORMALIZERS["identity"],
        "yelp_id": _NORMALIZERS["identity"],
        "mongo_objectid": _NORMALIZERS["objectid_to_str"],
        "unknown": _NORMALIZERS["identity"],
    }.get(fmt, _NORMALIZERS["identity"])


# ---------------------------------------------------------------------------
# JoinKeyResolver class
# ---------------------------------------------------------------------------

class JoinKeyResolver:
    """
    Auto-detects and resolves join key mismatches between two DataFrames.

    Example:
        resolver = JoinKeyResolver(df_a, 'customer_id', df_b, 'cid')
        merged = resolver.resolve_and_merge()
    """

    def __init__(
        self,
        df_a: pd.DataFrame,
        col_a: str,
        df_b: pd.DataFrame,
        col_b: str,
        how: str = "inner",
    ):
        self.df_a = df_a.copy()
        self.col_a = col_a
        self.df_b = df_b.copy()
        self.col_b = col_b
        self.how = how

        self.fmt_a = detect_format(df_a[col_a])
        self.fmt_b = detect_format(df_b[col_b])
        self.norm_a = get_normalizer(self.fmt_a)
        self.norm_b = get_normalizer(self.fmt_b)

    def resolve_and_merge(self, suffix: tuple[str, str] = ("_a", "_b")) -> pd.DataFrame:
        """
        Normalize both key columns to a common format and merge.
        Returns the merged DataFrame.
        """
        NORM_COL = "__join_key__"

        self.df_a[NORM_COL] = self.norm_a(self.df_a[self.col_a])
        self.df_b[NORM_COL] = self.norm_b(self.df_b[self.col_b])

        merged = pd.merge(
            self.df_a, self.df_b,
            on=NORM_COL,
            how=self.how,
            suffixes=suffix,
        )
        merged.drop(columns=[NORM_COL], inplace=True)
        return merged

    def describe(self) -> str:
        return (
            f"JoinKeyResolver: '{self.col_a}' (fmt={self.fmt_a}) "
            f"⟷ '{self.col_b}' (fmt={self.fmt_b})"
        )


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def resolve_join(
    df_a: pd.DataFrame,
    col_a: str,
    df_b: pd.DataFrame,
    col_b: str,
    how: str = "inner",
) -> pd.DataFrame:
    """
    One-call cross-database join with automatic key normalization.

    Args:
        df_a: Left DataFrame
        col_a: Join key column in df_a
        df_b: Right DataFrame
        col_b: Join key column in df_b
        how: 'inner', 'left', 'right', 'outer'

    Returns:
        Merged DataFrame
    """
    return JoinKeyResolver(df_a, col_a, df_b, col_b, how).resolve_and_merge()
