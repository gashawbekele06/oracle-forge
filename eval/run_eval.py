"""
Oracle Forge — Evaluation Harness
===================================
Runs the full evaluation pipeline:
  1. Loads benchmark results (from run_benchmark.py output)
  2. Scores against DAB ground truth
  3. Runs regression detection (compares to previous score log entry)
  4. Generates a structured evaluation report

Usage:
    python eval/run_eval.py --results results/benchmark_results.json
    python eval/run_eval.py --results results/benchmark_results.json --regression

This is the Sentinel-pattern evaluation harness described in the challenge spec.
Trace schema mirrors the Week 5 event-sourcing harness applied to data agent queries.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Allow import from parent
sys.path.insert(0, str(Path(__file__).parent))
from score import (
    load_ground_truth,
    compute_pass_at_1,
    is_correct,
    append_score_log,
)


# ---------------------------------------------------------------------------
# Failure category classification
# ---------------------------------------------------------------------------

FAILURE_CATEGORIES = {
    "multi_db_routing": [
        "only one database", "wrong database", "table not found",
        "no such table", "relation does not exist",
    ],
    "ill_formatted_join": [
        "0 rows", "empty result", "zero results", "join returned nothing",
        "CUST-", "format mismatch",
    ],
    "unstructured_extraction": [
        "raw text", "full text", "review text", "no extraction",
    ],
    "domain_knowledge": [
        "active customer", "churn", "fiscal", "definition",
    ],
}


def classify_failure(result: dict) -> str | None:
    """Attempt to classify a failed result into a DAB failure category."""
    if result.get("success"):
        return None

    reason = str(result.get("terminate_reason", "")).lower()
    answer = str(result.get("answer", "")).lower()
    text = reason + " " + answer

    for category, signals in FAILURE_CATEGORIES.items():
        if any(s in text for s in signals):
            return category
    return "unknown"


# ---------------------------------------------------------------------------
# Trace schema (Sentinel pattern)
# ---------------------------------------------------------------------------

def build_trace_entry(result: dict, is_correct_answer: bool, ground_truth: str) -> dict:
    """
    Build a structured trace entry per the Oracle Forge harness schema.
    Mirrors the Week 5 event-sourcing trace format.
    """
    return {
        "schema_version": "1.0",
        "timestamp": result.get("timestamp", datetime.now().isoformat()),
        "dataset": result.get("dataset"),
        "query_id": str(result.get("query_id")),
        "trial": result.get("run", 0),
        # Execution info
        "answer": result.get("answer", ""),
        "ground_truth": ground_truth,
        "is_correct": is_correct_answer,
        "terminate_reason": result.get("terminate_reason"),
        "llm_calls": result.get("llm_calls", 0),
        "retries": result.get("retries", 0),
        "duration_s": result.get("duration_s", 0),
        # Failure analysis
        "failure_category": classify_failure(result) if not is_correct_answer else None,
        "trace_path": result.get("trace_path"),
    }


# ---------------------------------------------------------------------------
# Regression detection
# ---------------------------------------------------------------------------

def check_regression(
    current_score: float,
    score_log_path: Path,
    threshold: float = 0.02,
) -> dict:
    """
    Compare current score against the previous entry in the score log.
    Returns a dict with regression info.
    """
    if not score_log_path.exists():
        return {"regression": False, "reason": "No previous score to compare"}

    entries = []
    with open(score_log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    if len(entries) < 2:
        return {"regression": False, "reason": "Only one score entry — baseline established"}

    prev = entries[-2]["overall_pass_at_1"]
    delta = current_score - prev

    if delta < -threshold:
        return {
            "regression": True,
            "previous": prev,
            "current": current_score,
            "delta": delta,
            "reason": f"Score dropped {abs(delta):.4f} (threshold: {threshold})",
        }
    return {
        "regression": False,
        "previous": prev,
        "current": current_score,
        "delta": delta,
        "reason": f"Score {'improved' if delta >= 0 else 'stable'} by {delta:.4f}",
    }


# ---------------------------------------------------------------------------
# Full evaluation report
# ---------------------------------------------------------------------------

def run_evaluation(
    results_path: Path,
    dab_root: Path,
    score_log_path: Path,
    traces_output: Path,
    check_regression_flag: bool = True,
) -> dict:
    """Run the full evaluation pipeline and return a structured report."""

    with open(results_path, encoding="utf-8") as f:
        results = json.load(f)

    ground_truth = load_ground_truth(dab_root)

    # Score
    scores = compute_pass_at_1(results, ground_truth)

    # Build per-result traces
    traces: list[dict] = []
    failure_counts: dict[str, int] = defaultdict(int)

    for result in results:
        key = (result["dataset"].lower(), str(result["query_id"]))
        truth = ground_truth.get(key, "")
        correct = is_correct(result.get("answer", ""), truth) if truth else False
        trace = build_trace_entry(result, correct, truth)
        traces.append(trace)
        if trace["failure_category"]:
            failure_counts[trace["failure_category"]] += 1

    # Save traces
    traces_output.parent.mkdir(parents=True, exist_ok=True)
    with open(traces_output, "w", encoding="utf-8") as f:
        json.dump(traces, f, indent=2)

    # Append to score log
    append_score_log(scores, score_log_path)

    # Regression check
    regression_result = {}
    if check_regression_flag:
        regression_result = check_regression(scores["overall"], score_log_path)

    report = {
        "timestamp": datetime.now().isoformat(),
        "results_file": str(results_path),
        "total_runs": len(results),
        "total_queries": scores["total_queries"],
        "passed_queries": scores["passed_queries"],
        "overall_pass_at_1": scores["overall"],
        "by_dataset": scores["by_dataset"],
        "failure_breakdown": dict(failure_counts),
        "regression": regression_result,
        "traces_saved_to": str(traces_output),
    }

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    _root = Path(__file__).parent.parent

    parser = argparse.ArgumentParser(
        description="Oracle Forge — Full Evaluation Harness (Sentinel pattern)"
    )
    parser.add_argument("--results", required=True)
    parser.add_argument("--dab_root", default=str(_root / "DataAgentBench"))
    parser.add_argument("--score_log", default=str(_root / "eval" / "score_log.jsonl"))
    parser.add_argument("--traces_output", default=str(_root / "eval" / "traces.json"))
    parser.add_argument("--regression", action="store_true", default=True)
    parser.add_argument("--report_output", default=str(_root / "eval" / "eval_report.json"))
    args = parser.parse_args()

    report = run_evaluation(
        results_path=Path(args.results),
        dab_root=Path(args.dab_root),
        score_log_path=Path(args.score_log),
        traces_output=Path(args.traces_output),
        check_regression_flag=args.regression,
    )

    # Save report
    with open(args.report_output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print(f"\n{'='*55}")
    print(f"Oracle Forge — Evaluation Report")
    print(f"{'='*55}")
    print(f"Overall pass@1: {report['overall_pass_at_1']:.4f}")
    print(f"Queries:        {report['passed_queries']}/{report['total_queries']}")
    print(f"\nFailure breakdown:")
    for cat, count in report["failure_breakdown"].items():
        print(f"  {cat:30s}: {count}")

    reg = report.get("regression", {})
    if reg:
        status = "⚠️  REGRESSION DETECTED" if reg.get("regression") else "✅ No regression"
        print(f"\nRegression check: {status}")
        print(f"  {reg.get('reason', '')}")

    print(f"\nReport saved: {args.report_output}")
    print(f"Score log:    {args.score_log}")

    if reg.get("regression"):
        sys.exit(1)  # Signal regression to CI


if __name__ == "__main__":
    main()
