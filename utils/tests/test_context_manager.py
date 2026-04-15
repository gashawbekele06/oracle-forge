"""
Tests for agent/context_manager.py — Three-Layer Context Architecture

Maps to Challenge 1 (multi-layer context architecture) and the interim
submission requirement: KB v1 + KB v2 committed with injection test evidence.

Layer 1 — Schema & metadata (db_description.txt from DAB)
Layer 2 — Domain KB (join_keys, terminology, schemas, unstructured_fields)
Layer 3 — Corrections log (past failures → correct approaches)
"""

import sys
import os
import tempfile
from pathlib import Path

import pytest

# ── path bootstrap ────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agent"))

from agent.context_manager import ContextManager


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def fake_kb(tmp_path: Path) -> Path:
    """Create a minimal KB directory tree with all three layers."""
    # Layer 2 — domain
    domain = tmp_path / "domain"
    domain.mkdir()
    (domain / "join_keys.md").write_text(
        "- yelp business_id: 22-char alphanumeric string\n"
        "- crmarenapro customer_id: integer (PostgreSQL) vs CUST-XXXXXXX (DuckDB)\n",
        encoding="utf-8",
    )
    (domain / "terminology.md").write_text(
        "- churn: customer with no purchase in last 90 days\n"
        "- active account: status_code IN ('A', 'ACT', 'ACTIVE')\n",
        encoding="utf-8",
    )
    (domain / "schemas.md").write_text(
        "- yelp.business: id, name, stars, city, state\n"
        "- crmarenapro.orders: order_id, customer_id, total_amount\n",
        encoding="utf-8",
    )
    (domain / "unstructured_fields.md").write_text(
        "- yelp.review.text: free-form review text; use regex/NLP, not SQL LIKE\n"
        "- agnews.article.content: news article body; use keyword extraction\n",
        encoding="utf-8",
    )

    # Layer 3 — corrections
    corrections = tmp_path / "corrections"
    corrections.mkdir()
    (corrections / "corrections_log.md").write_text(
        "# Corrections Log\n\n"
        "---\n"
        "**Dataset**: crmarenapro | **Query**: 3\n\n"
        "**Query**: Which customers appear in both tickets and orders?\n\n"
        "**What went wrong**: Direct join on customer_id returned 0 rows "
        "because DuckDB uses CUST-0001001 and PostgreSQL uses integer 1001.\n\n"
        "**Correct approach**: Strip CUST- prefix and leading zeros before joining.\n",
        encoding="utf-8",
    )

    # Layer 1 — fake DAB dataset
    dab = tmp_path / "DataAgentBench"
    query_yelp = dab / "query_yelp"
    query_yelp.mkdir(parents=True)
    (query_yelp / "db_description.txt").write_text(
        "Table: business (id TEXT, name TEXT, stars REAL, city TEXT, state TEXT)\n"
        "Table: review (id TEXT, business_id TEXT, user_id TEXT, stars REAL, text TEXT)\n",
        encoding="utf-8",
    )
    (query_yelp / "db_description_withhint.txt").write_text(
        "HINT: business_id is a 22-character alphanumeric Yelp ID.\n"
        "HINT: Use execute_python for text analysis on review.text.\n",
        encoding="utf-8",
    )

    return tmp_path


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1 — Schema
# ─────────────────────────────────────────────────────────────────────────────

class TestLayer1Schema:
    def test_schema_section_present(self, fake_kb):
        """Layer 1 header must appear in built context."""
        mgr = ContextManager(kb_root=fake_kb, dab_root=fake_kb / "DataAgentBench")
        ctx = mgr.build("yelp")
        assert "DATABASE DESCRIPTION" in ctx
        assert "Layer 1" in ctx

    def test_schema_contains_table_names(self, fake_kb):
        """db_description.txt tables must be injected."""
        mgr = ContextManager(kb_root=fake_kb, dab_root=fake_kb / "DataAgentBench")
        ctx = mgr.build("yelp")
        assert "business" in ctx
        assert "review" in ctx

    def test_hints_included_by_default(self, fake_kb):
        """db_description_withhint.txt content must be included when use_hints=True."""
        mgr = ContextManager(kb_root=fake_kb, dab_root=fake_kb / "DataAgentBench")
        ctx = mgr.build("yelp", use_hints=True)
        assert "HINT" in ctx

    def test_hints_excluded_when_disabled(self, fake_kb):
        """use_hints=False must omit withhint content."""
        mgr = ContextManager(kb_root=fake_kb, dab_root=fake_kb / "DataAgentBench")
        ctx = mgr.build("yelp", use_hints=False)
        assert "HINT" not in ctx

    def test_missing_dataset_does_not_crash(self, fake_kb):
        """Unknown dataset → graceful fallback, not exception."""
        mgr = ContextManager(kb_root=fake_kb, dab_root=fake_kb / "DataAgentBench")
        ctx = mgr.build("nonexistent_dataset")
        assert isinstance(ctx, str)
        assert len(ctx) > 0


# ─────────────────────────────────────────────────────────────────────────────
# Layer 2 — Domain KB
# ─────────────────────────────────────────────────────────────────────────────

class TestLayer2DomainKB:
    def test_domain_section_present(self, fake_kb):
        """Layer 2 header must appear in built context."""
        mgr = ContextManager(kb_root=fake_kb, dab_root=fake_kb / "DataAgentBench")
        ctx = mgr.build("yelp")
        assert "DOMAIN KNOWLEDGE" in ctx
        assert "Layer 2" in ctx

    def test_join_keys_injected(self, fake_kb):
        """Join key glossary must appear in context."""
        mgr = ContextManager(kb_root=fake_kb, dab_root=fake_kb / "DataAgentBench")
        ctx = mgr.build("yelp")
        assert "business_id" in ctx
        assert "22-char" in ctx

    def test_terminology_injected(self, fake_kb):
        """Domain terminology (churn, active account) must appear."""
        mgr = ContextManager(kb_root=fake_kb, dab_root=fake_kb / "DataAgentBench")
        ctx = mgr.build("yelp")
        assert "churn" in ctx
        assert "status_code" in ctx

    def test_unstructured_fields_injected(self, fake_kb):
        """Unstructured field inventory must appear — directs agent away from SQL LIKE."""
        mgr = ContextManager(kb_root=fake_kb, dab_root=fake_kb / "DataAgentBench")
        ctx = mgr.build("yelp")
        assert "review.text" in ctx
        assert "regex" in ctx.lower() or "nlp" in ctx.lower()

    def test_empty_kb_produces_output(self, tmp_path):
        """ContextManager with empty KB still returns a string, not an error."""
        # DAB with minimal schema
        dab = tmp_path / "DataAgentBench" / "query_yelp"
        dab.mkdir(parents=True)
        (dab / "db_description.txt").write_text("Table: business\n", encoding="utf-8")

        mgr = ContextManager(kb_root=tmp_path / "empty_kb", dab_root=tmp_path / "DataAgentBench")
        ctx = mgr.build("yelp")
        assert isinstance(ctx, str)
        assert "business" in ctx


# ─────────────────────────────────────────────────────────────────────────────
# Layer 3 — Corrections Log
# ─────────────────────────────────────────────────────────────────────────────

class TestLayer3Corrections:
    def test_corrections_section_present(self, fake_kb):
        """Layer 3 header must appear when corrections file exists."""
        mgr = ContextManager(kb_root=fake_kb, dab_root=fake_kb / "DataAgentBench")
        ctx = mgr.build("yelp")
        assert "KNOWN CORRECTIONS" in ctx
        assert "Layer 3" in ctx

    def test_corrections_content_injected(self, fake_kb):
        """Known failure + correct approach must be visible in context."""
        mgr = ContextManager(kb_root=fake_kb, dab_root=fake_kb / "DataAgentBench")
        ctx = mgr.build("yelp")
        assert "CUST-" in ctx
        assert "Strip" in ctx or "prefix" in ctx.lower()

    def test_append_correction_writes_to_file(self, fake_kb):
        """append_correction must add a new entry to corrections_log.md."""
        mgr = ContextManager(kb_root=fake_kb, dab_root=fake_kb / "DataAgentBench")
        mgr.append_correction(
            dataset="yelp",
            query_id="7",
            query_text="How many reviews mention 'slow service'?",
            what_went_wrong="SQL LIKE '%slow%' matched unrelated rows.",
            correct_approach="Fetch review.text, apply regex in execute_python.",
        )
        log = (fake_kb / "corrections" / "corrections_log.md").read_text(encoding="utf-8")
        assert "yelp" in log
        assert "7" in log
        assert "SQL LIKE" in log
        assert "execute_python" in log

    def test_corrections_excluded_when_disabled(self, fake_kb):
        """include_corrections=False must omit Layer 3."""
        mgr = ContextManager(kb_root=fake_kb, dab_root=fake_kb / "DataAgentBench")
        ctx = mgr.build("yelp", include_corrections=False)
        assert "KNOWN CORRECTIONS" not in ctx

    def test_append_creates_file_if_missing(self, tmp_path):
        """append_correction must create corrections_log.md if it does not exist."""
        mgr = ContextManager(kb_root=tmp_path / "kb", dab_root=tmp_path / "dab")
        mgr.append_correction(
            dataset="stockmarket",
            query_id="2",
            query_text="What is the average daily return for AAPL?",
            what_went_wrong="Missing pct_change groupby.",
            correct_approach="Use df.groupby('ticker')['close'].pct_change().",
        )
        log_path = tmp_path / "kb" / "corrections" / "corrections_log.md"
        assert log_path.exists()
        content = log_path.read_text(encoding="utf-8")
        assert "stockmarket" in content
        assert "pct_change" in content


# ─────────────────────────────────────────────────────────────────────────────
# Integration — All three layers together
# ─────────────────────────────────────────────────────────────────────────────

class TestAllLayersTogether:
    def test_context_has_all_three_sections(self, fake_kb):
        """All three layer headers must be present in a single build() call."""
        mgr = ContextManager(kb_root=fake_kb, dab_root=fake_kb / "DataAgentBench")
        ctx = mgr.build("yelp")
        assert "Layer 1" in ctx
        assert "Layer 2" in ctx
        assert "Layer 3" in ctx

    def test_context_is_non_empty_string(self, fake_kb):
        """build() must return a non-empty string."""
        mgr = ContextManager(kb_root=fake_kb, dab_root=fake_kb / "DataAgentBench")
        ctx = mgr.build("yelp")
        assert isinstance(ctx, str)
        assert len(ctx) > 100

    def test_context_sections_are_ordered(self, fake_kb):
        """Layer 1 must appear before Layer 2, which must appear before Layer 3."""
        mgr = ContextManager(kb_root=fake_kb, dab_root=fake_kb / "DataAgentBench")
        ctx = mgr.build("yelp")
        pos1 = ctx.index("Layer 1")
        pos2 = ctx.index("Layer 2")
        pos3 = ctx.index("Layer 3")
        assert pos1 < pos2 < pos3

    def test_architecture_context_returns_string(self, fake_kb):
        """get_architecture_context() should return a string (empty if files missing)."""
        mgr = ContextManager(kb_root=fake_kb, dab_root=fake_kb / "DataAgentBench")
        arch = mgr.get_architecture_context()
        assert isinstance(arch, str)
