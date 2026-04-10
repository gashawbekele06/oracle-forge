"""Tests for utils/multi_pass_retrieval.py"""

import sys
from pathlib import Path
import pytest
import tempfile
import os

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.multi_pass_retrieval import (
    expand_query,
    parse_corrections_log,
    keyword_score,
    MultiPassRetriever,
    CorrectionEntry,
)


SAMPLE_LOG = """# Corrections Log

---
**Dataset**: crmarenapro | **Query**: 3

**Query**: Which customers appear in both tickets and orders?

**What went wrong**: Direct join on customer_id produced 0 rows because DuckDB tickets use CUST-0001001 format while PostgreSQL uses integer 1001.

**Correct approach**: Strip CUST- prefix and leading zeros before joining with pandas merge.

---
**Dataset**: yelp | **Query**: 5

**Query**: How many reviews mention slow service?

**What went wrong**: Agent used SQL LIKE '%slow%' which counted unrelated mentions.

**Correct approach**: Fetch reviews, use regex in execute_python to detect complaint patterns.
"""


# ---------------------------------------------------------------------------
# expand_query
# ---------------------------------------------------------------------------

def test_expand_query_join_key():
    terms = expand_query("join key mismatch")
    assert "join key mismatch" in terms
    assert any("CUST" in t or "prefix" in t for t in terms)


def test_expand_query_no_expansion():
    terms = expand_query("completely unrelated term xyz123")
    assert terms[0] == "completely unrelated term xyz123"
    assert len(terms) >= 1


# ---------------------------------------------------------------------------
# parse_corrections_log
# ---------------------------------------------------------------------------

def test_parse_corrections_log():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(SAMPLE_LOG)
        tmp_path = f.name

    try:
        entries = parse_corrections_log(Path(tmp_path))
        assert len(entries) == 2
        assert entries[0].dataset == "crmarenapro"
        assert entries[0].query_id == "3"
        assert "CUST-" in entries[0].what_went_wrong or "0 rows" in entries[0].what_went_wrong
        assert "Strip" in entries[0].correct_approach or "prefix" in entries[0].correct_approach

        assert entries[1].dataset == "yelp"
        assert entries[1].query_id == "5"
    finally:
        os.unlink(tmp_path)


def test_parse_empty_log():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write("# Corrections Log\n\nNo entries yet.\n")
        tmp_path = f.name
    try:
        entries = parse_corrections_log(Path(tmp_path))
        assert entries == []
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# MultiPassRetriever
# ---------------------------------------------------------------------------

def test_retriever_finds_relevant_entry():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(SAMPLE_LOG)
        tmp_path = f.name

    try:
        retriever = MultiPassRetriever(kb_path=tmp_path)
        results = retriever.search("customer id format CUST prefix join issue")
        assert len(results) > 0
        assert any("crmarenapro" in r.dataset for r in results)
    finally:
        os.unlink(tmp_path)


def test_retriever_returns_empty_for_irrelevant_query():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(SAMPLE_LOG)
        tmp_path = f.name

    try:
        retriever = MultiPassRetriever(kb_path=tmp_path, min_score=0.9)
        results = retriever.search("completely unrelated zygote biology quantum")
        assert len(results) == 0
    finally:
        os.unlink(tmp_path)


def test_retriever_format_results():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(SAMPLE_LOG)
        tmp_path = f.name

    try:
        retriever = MultiPassRetriever(kb_path=tmp_path)
        results = retriever.search("CUST prefix")
        formatted = retriever.format_results(results)
        assert "Dataset" in formatted or "Wrong" in formatted or "Correct" in formatted
    finally:
        os.unlink(tmp_path)


def test_retriever_missing_file():
    retriever = MultiPassRetriever(kb_path="/nonexistent/path.md")
    results = retriever.search("anything")
    assert results == []
