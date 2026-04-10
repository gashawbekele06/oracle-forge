"""
Oracle Forge — Three-Layer Context Manager

Implements the three mandatory context layers from the challenge spec:
  Layer 1 (schema)       — database schema + metadata for all connected DBs
  Layer 2 (domain)       — KB documents: join keys, terminology, schemas, unstructured fields
  Layer 3 (corrections)  — running log of agent failures → correct approach

Usage:
    mgr = ContextManager(kb_root="kb/", dab_root="DataAgentBench/")
    system_addendum = mgr.build(dataset="yelp")
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_md(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def _read_db_description(dab_root: Path, dataset: str, use_hints: bool = True) -> str:
    """Read DAB db_description (+ optional hints) for the given dataset."""
    dataset_key = dataset.upper() if dataset in {"DEPS_DEV_V1", "GITHUB_REPOS",
                                                  "PANCANCER_ATLAS", "PATENTS"} else dataset
    query_dir = dab_root / f"query_{dataset_key}"

    # Try both cased versions
    if not query_dir.exists():
        query_dir = dab_root / f"query_{dataset.lower()}"
    if not query_dir.exists():
        query_dir = dab_root / f"query_{dataset}"

    desc_path = query_dir / "db_description.txt"
    if not desc_path.exists():
        return f"[Schema not found for dataset '{dataset}']"

    desc = desc_path.read_text(encoding="utf-8").strip()

    if use_hints:
        hint_path = query_dir / "db_description_withhint.txt"
        if hint_path.exists():
            desc += "\n\n" + hint_path.read_text(encoding="utf-8").strip()

    return desc


# ---------------------------------------------------------------------------
# ContextManager
# ---------------------------------------------------------------------------

class ContextManager:
    """
    Builds the combined context injected into the agent's system prompt.

    Layer 1 — Schema & metadata (from DAB db_description.txt + hints)
    Layer 2 — Domain KB (join_keys, schemas, terminology, unstructured_fields)
    Layer 3 — Corrections log (past failures → correct approaches)
    """

    def __init__(
        self,
        kb_root: str | Path = "kb",
        dab_root: str | Path = "DataAgentBench",
    ):
        self.kb_root = Path(kb_root)
        self.dab_root = Path(dab_root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        dataset: str,
        use_hints: bool = True,
        include_corrections: bool = True,
    ) -> str:
        """
        Return the full context string to append after the base system prompt.

        Args:
            dataset: DAB dataset name (e.g. "yelp", "bookreview")
            use_hints: whether to include db_description_withhint.txt
            include_corrections: whether to load corrections log (Layer 3)
        """
        parts: list[str] = []

        # ── Layer 1: Schema & metadata ──────────────────────────────────
        schema = _read_db_description(self.dab_root, dataset, use_hints)
        parts.append(self._section("DATABASE DESCRIPTION (Layer 1 — Schema)", schema))

        # ── Layer 2: Domain KB ──────────────────────────────────────────
        domain_parts: list[str] = []

        join_keys = _read_md(self.kb_root / "domain" / "join_keys.md")
        if join_keys:
            domain_parts.append(f"### Join Key Glossary\n{join_keys}")

        terminology = _read_md(self.kb_root / "domain" / "terminology.md")
        if terminology:
            domain_parts.append(f"### Domain Terminology\n{terminology}")

        schemas = _read_md(self.kb_root / "domain" / "schemas.md")
        if schemas:
            domain_parts.append(f"### Schema Notes\n{schemas}")

        unstructured = _read_md(self.kb_root / "domain" / "unstructured_fields.md")
        if unstructured:
            domain_parts.append(f"### Unstructured Field Inventory\n{unstructured}")

        # Dataset-specific domain KB (if exists)
        dataset_kb = _read_md(self.kb_root / "domain" / f"{dataset.lower()}.md")
        if dataset_kb:
            domain_parts.append(f"### Dataset-Specific Notes ({dataset})\n{dataset_kb}")

        if domain_parts:
            parts.append(self._section(
                "DOMAIN KNOWLEDGE (Layer 2 — Knowledge Base)",
                "\n\n".join(domain_parts),
            ))

        # ── Layer 3: Corrections log ─────────────────────────────────────
        if include_corrections:
            corrections = _read_md(self.kb_root / "corrections" / "corrections_log.md")
            if corrections:
                parts.append(self._section(
                    "KNOWN CORRECTIONS (Layer 3 — Corrections Log)",
                    corrections,
                ))

        return "\n\n".join(parts)

    def append_correction(
        self,
        dataset: str,
        query_id: str,
        query_text: str,
        what_went_wrong: str,
        correct_approach: str,
    ) -> None:
        """
        Append a new entry to the corrections log (Layer 3).
        Called automatically by OracleAgent after a failed run.
        """
        log_path = self.kb_root / "corrections" / "corrections_log.md"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        existing = _read_md(log_path)

        entry = (
            f"\n\n---\n"
            f"**Dataset**: {dataset} | **Query**: {query_id}\n\n"
            f"**Query**: {query_text[:300]}\n\n"
            f"**What went wrong**: {what_went_wrong}\n\n"
            f"**Correct approach**: {correct_approach}\n"
        )

        with open(log_path, "a", encoding="utf-8") as f:
            if not existing:
                f.write("# Corrections Log\n\nRunning log of agent failures and correct approaches.\n")
            f.write(entry)

    def get_architecture_context(self) -> str:
        """Return architecture KB documents (used to prime intelligence work)."""
        arch_parts: list[str] = []
        for fname in ["claude_code_memory.md", "openai_data_agent.md", "tool_design.md",
                      "context_layers.md", "memory_system.md"]:
            content = _read_md(self.kb_root / "architecture" / fname)
            if content:
                arch_parts.append(f"### {fname}\n{content}")
        return "\n\n".join(arch_parts)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _section(title: str, content: str) -> str:
        bar = "=" * 60
        return f"{bar}\n## {title}\n{bar}\n{content}"
