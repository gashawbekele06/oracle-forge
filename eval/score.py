"""
Oracle Forge — Scoring Script
================================
Computes pass@1 scores against DAB ground truth.

Usage:
    python eval/score.py --results results/benchmark_results.json
    python eval/score.py --results results/benchmark_results.json --verbose
    python eval/score.py --results results/benchmark_results.json --output eval/score_log.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Answer comparison
# ---------------------------------------------------------------------------

def normalize_answer(ans: str) -> str:
    """Normalize an answer string for comparison."""
    if not ans:
        return ""
    ans = str(ans).strip().lower()
    # Remove trailing punctuation
    ans = re.sub(r"[.,;:!?]+$", "", ans)
    # Collapse whitespace
    ans = re.sub(r"\s+", " ", ans)
    return ans


def numeric_match(pred: str, truth: str, tolerance: float = 0.01) -> bool:
    """Return True if both are numeric and within tolerance percent."""
    try:
        p = float(re.sub(r"[,$%]", "", pred))
        t = float(re.sub(r"[,$%]", "", truth))
        if t == 0:
            return abs(p) < 1e-9
        return abs(p - t) / abs(t) <= tolerance
    except (ValueError, ZeroDivisionError):
        return False


def is_correct(predicted: str, ground_truth: str) -> bool:
    """
    Flexible answer comparison:
    1. Exact string match (after normalization)
    2. Numeric match within 1%
    3. For lists: set intersection / subset check
    """
    pred_norm = normalize_answer(predicted)
    truth_norm = normalize_answer(ground_truth)

    if pred_norm == truth_norm:
        return True

    if numeric_match(pred_norm, truth_norm):
        return True

    # Set match for comma/newline-separated lists
    if "," in truth_norm or "\n" in truth_norm:
        truth_set = {normalize_answer(x) for x in re.split(r"[,\n]", truth_norm) if x.strip()}
        pred_set = {normalize_answer(x) for x in re.split(r"[,\n]", pred_norm) if x.strip()}
        if truth_set and truth_set == pred_set:
            return True
        if truth_set and truth_set.issubset(pred_set):
            return True

    return False


# ---------------------------------------------------------------------------
# Ground truth loader
# ---------------------------------------------------------------------------

def load_ground_truth(dab_root: Path) -> dict[tuple[str, str], str]:
    """
    Load ground truth answers from DataAgentBench query directories.
    Returns: {(dataset, query_id): answer_string}
    """
    gt: dict[tuple[str, str], str] = {}

    for query_dir in sorted(dab_root.glob("query_*/query*")):
        answer_path = query_dir / "answer.txt"
        if not answer_path.exists():
            continue

        parts = query_dir.parts
        # Parent dir: query_yelp → dataset = "yelp"
        parent_name = query_dir.parent.name  # e.g. query_yelp
        dataset = parent_name.replace("query_", "")
        query_id = query_dir.name.replace("query", "")  # e.g. "1"

        gt[(dataset.lower(), query_id)] = answer_path.read_text(encoding="utf-8").strip()

    return gt


# ---------------------------------------------------------------------------
# Pass@1 computation
# ---------------------------------------------------------------------------

def compute_pass_at_1(
    results: list[dict],
    ground_truth: dict[tuple[str, str], str],
) -> dict:
    """
    Compute pass@1 overall and by dataset.

    Returns:
    {
        "overall": float,
        "by_dataset": {dataset: float},
        "by_query": {(dataset, query_id): bool},
        "details": [...]
    }
    """
    # Group by (dataset, query_id) → list of answers across trials
    query_answers: dict[tuple[str, str], list[str]] = defaultdict(list)
    for r in results:
        key = (r["dataset"].lower(), str(r["query_id"]))
        query_answers[key].append(r.get("answer", ""))

    by_query: dict[tuple[str, str], bool] = {}
    details: list[dict] = []

    for (dataset, query_id), answers in query_answers.items():
        truth = ground_truth.get((dataset, query_id), "")
        if not truth:
            continue  # No ground truth — skip

        passed = any(is_correct(a, truth) for a in answers)
        by_query[(dataset, query_id)] = passed

        details.append({
            "dataset": dataset,
            "query_id": query_id,
            "passed": passed,
            "trials": len(answers),
            "ground_truth": truth[:100],
            "best_answer": max(answers, key=lambda a: is_correct(a, truth)) if answers else "",
        })

    # Overall pass@1
    if not by_query:
        overall = 0.0
    else:
        overall = sum(by_query.values()) / len(by_query)

    # By dataset
    dataset_scores: dict[str, list[bool]] = defaultdict(list)
    for (dataset, _), passed in by_query.items():
        dataset_scores[dataset].append(passed)

    by_dataset = {
        ds: sum(scores) / len(scores)
        for ds, scores in dataset_scores.items()
    }

    return {
        "overall": overall,
        "by_dataset": by_dataset,
        "by_query": {f"{k[0]}/q{k[1]}": v for k, v in by_query.items()},
        "details": sorted(details, key=lambda d: (d["dataset"], int(d["query_id"]))),
        "total_queries": len(by_query),
        "passed_queries": sum(by_query.values()),
    }


# ---------------------------------------------------------------------------
# Score log
# ---------------------------------------------------------------------------

def append_score_log(score_result: dict, log_path: Path) -> None:
    """Append a score entry to the JSONL score log."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "overall_pass_at_1": score_result["overall"],
        "total_queries": score_result["total_queries"],
        "passed_queries": score_result["passed_queries"],
        "by_dataset": score_result["by_dataset"],
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    _root = Path(__file__).parent.parent

    parser = argparse.ArgumentParser(
        description="Score Oracle Forge benchmark results against DAB ground truth"
    )
    parser.add_argument("--results", required=True, help="Path to benchmark_results.json")
    parser.add_argument("--dab_root", default=str(_root / "DataAgentBench"))
    parser.add_argument("--output", default=str(_root / "eval" / "score_log.jsonl"))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    results_path = Path(args.results)
    if not results_path.exists():
        print(f"ERROR: Results file not found: {results_path}", file=sys.stderr)
        sys.exit(1)

    with open(results_path, encoding="utf-8") as f:
        results = json.load(f)

    dab_root = Path(args.dab_root)
    ground_truth = load_ground_truth(dab_root)

    if not ground_truth:
        print("WARNING: No ground truth found. Cannot score.", file=sys.stderr)
        print(f"         Expected answer.txt files in: {dab_root}/query_*/query*/answer.txt")
        sys.exit(1)

    scores = compute_pass_at_1(results, ground_truth)

    # Print summary
    print(f"\n{'='*50}")
    print(f"Oracle Forge — DAB Evaluation Scores")
    print(f"{'='*50}")
    print(f"Overall pass@1:  {scores['overall']:.4f}  ({scores['passed_queries']}/{scores['total_queries']} queries)")
    print(f"\nBy dataset:")
    for ds, score in sorted(scores["by_dataset"].items()):
        print(f"  {ds:20s}: {score:.4f}")

    if args.verbose:
        print(f"\nBy query:")
        for detail in scores["details"]:
            status = "✅" if detail["passed"] else "❌"
            print(f"  {status} {detail['dataset']}/q{detail['query_id']} "
                  f"({detail['trials']} trials) "
                  f"truth='{detail['ground_truth'][:40]}...'")

    print(f"\nScore log: {args.output}")
    append_score_log(scores, Path(args.output))


if __name__ == "__main__":
    main()
