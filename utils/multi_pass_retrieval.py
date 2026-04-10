"""
Oracle Forge — Multi-Pass Retrieval Helper
============================================
Implements the multi-pass semantic retrieval strategy from the
AI Agent Internals probing methodology (strategy document).

Motivation: A single semantic search pass for "corrections" misses
corrections phrased as intellectual disagreement rather than "mistake."
Multiple passes with different vocabulary → deduplicate → merge.

Usage:
    from utils.multi_pass_retrieval import MultiPassRetriever

    retriever = MultiPassRetriever(kb_path="kb/corrections/corrections_log.md")
    results = retriever.search("customer id format mismatch")
    print(results)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CorrectionEntry:
    dataset: str
    query_id: str
    query_text: str
    what_went_wrong: str
    correct_approach: str
    raw_text: str = ""
    score: float = 0.0


# ---------------------------------------------------------------------------
# Vocabulary expansion for multi-pass
# ---------------------------------------------------------------------------

QUERY_EXPANSIONS: dict[str, list[str]] = {
    # Join key issues
    "join key": ["format mismatch", "CUST prefix", "customer id", "ill-formatted", "0 rows after join"],
    "format mismatch": ["CUST-", "C{id}", "prefix", "strip", "normalize", "integer vs string"],
    # Multi-DB routing
    "wrong database": ["only one db", "missing data", "single database", "routing failure"],
    "cross db": ["cross-database", "multi-database", "two databases", "separate query"],
    # Unstructured
    "text extraction": ["raw text", "LIKE query", "regex", "sentiment", "unstructured"],
    "sentiment": ["negative", "complaint", "positive review", "rating", "stars"],
    # Domain knowledge
    "active customer": ["90 days", "churn", "last purchase", "last_purchase_date"],
    "revenue": ["refunded", "cancelled", "exclude", "status", "amount"],
    # General
    "correction": ["pushed back", "disagreed", "wrong", "actually", "that is not right", "incorrect"],
}


def expand_query(query: str) -> list[str]:
    """Return the original query plus expanded variants."""
    queries = [query.lower()]
    for key, expansions in QUERY_EXPANSIONS.items():
        if key in query.lower():
            queries.extend(e.lower() for e in expansions)
    return list(dict.fromkeys(queries))  # deduplicate, preserve order


# ---------------------------------------------------------------------------
# Corrections log parser
# ---------------------------------------------------------------------------

_ENTRY_PATTERN = re.compile(
    r"\*\*Dataset\*\*: (?P<dataset>[^\|]+)\s*\|\s*\*\*Query\*\*: (?P<query_id>[^\n]+)\n+"
    r"\*\*Query\*\*: (?P<query_text>[^\n]+)\n+"
    r"\*\*What went wrong\*\*: (?P<wrong>[^\n]+(?:\n(?!\*\*)[^\n]*)*)\n+"
    r"\*\*Correct approach\*\*: (?P<correct>[^\n]+(?:\n(?!---|\*\*Dataset\*\*)[^\n]*)*)",
    re.MULTILINE,
)


def parse_corrections_log(log_path: Path) -> list[CorrectionEntry]:
    """Parse the corrections_log.md into structured CorrectionEntry objects."""
    if not log_path.exists():
        return []

    text = log_path.read_text(encoding="utf-8")
    entries: list[CorrectionEntry] = []

    for m in _ENTRY_PATTERN.finditer(text):
        entries.append(CorrectionEntry(
            dataset=m.group("dataset").strip(),
            query_id=m.group("query_id").strip(),
            query_text=m.group("query_text").strip(),
            what_went_wrong=m.group("wrong").strip(),
            correct_approach=m.group("correct").strip(),
            raw_text=m.group(0),
        ))

    return entries


# ---------------------------------------------------------------------------
# Scoring (simple keyword overlap)
# ---------------------------------------------------------------------------

def keyword_score(entry: CorrectionEntry, query_terms: list[str]) -> float:
    """Score a correction entry against a list of query terms (0.0–1.0)."""
    text = " ".join([
        entry.dataset, entry.query_text,
        entry.what_went_wrong, entry.correct_approach,
    ]).lower()

    matched = sum(1 for term in query_terms if term in text)
    return matched / max(len(query_terms), 1)


# ---------------------------------------------------------------------------
# MultiPassRetriever
# ---------------------------------------------------------------------------

class MultiPassRetriever:
    """
    Retrieves relevant correction entries using multi-pass vocabulary expansion.

    Algorithm (from AI Agent Internals strategy doc):
      pass_1 → search with original query
      pass_2 → search with vocabulary-expanded variants
      pass_3 → deduplicate by entry identity, rank by aggregate score
    """

    def __init__(
        self,
        kb_path: str | Path = "kb/corrections/corrections_log.md",
        top_k: int = 5,
        min_score: float = 0.1,
    ):
        self.kb_path = Path(kb_path)
        self.top_k = top_k
        self.min_score = min_score
        self._entries: list[CorrectionEntry] | None = None

    @property
    def entries(self) -> list[CorrectionEntry]:
        if self._entries is None:
            self._entries = parse_corrections_log(self.kb_path)
        return self._entries

    def reload(self) -> None:
        """Force reload of corrections log (call after new entries added)."""
        self._entries = None

    def search(self, query: str) -> list[CorrectionEntry]:
        """
        Multi-pass retrieval: search with original + expanded query terms.
        Returns top-k entries sorted by relevance score.
        """
        if not self.entries:
            return []

        all_terms = expand_query(query)

        # Score each entry against all terms (aggregate)
        scored: dict[int, float] = {}
        for i, entry in enumerate(self.entries):
            score = keyword_score(entry, all_terms)
            if score >= self.min_score:
                scored[i] = score

        # Sort by score descending, take top_k
        top_indices = sorted(scored, key=lambda i: scored[i], reverse=True)[:self.top_k]

        results = []
        for idx in top_indices:
            entry = self.entries[idx]
            entry.score = scored[idx]
            results.append(entry)

        return results

    def format_results(self, results: list[CorrectionEntry]) -> str:
        """Format retrieval results for injection into agent context."""
        if not results:
            return "No relevant corrections found."

        parts = []
        for r in results:
            parts.append(
                f"**Dataset**: {r.dataset} | **Query**: {r.query_id}\n"
                f"**Wrong**: {r.what_went_wrong[:200]}\n"
                f"**Correct**: {r.correct_approach[:400]}"
            )
        return "\n\n---\n\n".join(parts)

    def search_and_format(self, query: str) -> str:
        """Convenience: search and return formatted string."""
        return self.format_results(self.search(query))
