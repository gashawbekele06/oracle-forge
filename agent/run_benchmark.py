"""
Oracle Forge — Benchmark Runner
================================
Runs the OracleAgent against DataAgentBench queries and produces
a results JSON file ready for DAB leaderboard submission.

Usage (single query):
    python run_benchmark.py --dataset yelp --query_id 1 --llm claude-opus-4-6

Usage (full benchmark, 5 trials each):
    python run_benchmark.py --all --trials 5 --llm claude-opus-4-6

Usage (specific datasets):
    python run_benchmark.py --datasets yelp bookreview --trials 3 --llm claude-sonnet-4-6

Docker usage:
    docker compose run agent python run_benchmark.py --all --trials 5
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Allow import from DataAgentBench
_DIR = Path(__file__).parent
_DAB_ROOT = Path(os.getenv("DAB_ROOT", str(_DIR.parent / "DataAgentBench")))
sys.path.insert(0, str(_DAB_ROOT))
sys.path.insert(0, str(_DIR))

from oracle_agent import OracleAgent

# ---------------------------------------------------------------------------
# Dataset registry — maps dataset name → list of query IDs
# ---------------------------------------------------------------------------

DATASET_QUERIES: dict[str, list[int]] = {
    "agnews":         [1, 2, 3, 4],
    "bookreview":     [1, 2, 3],
    "crmarenapro":    list(range(1, 14)),
    "DEPS_DEV_V1":    [1, 2],
    "GITHUB_REPOS":   [1, 2, 3, 4],
    "googlelocal":    [1, 2, 3, 4],
    "music_brainz_20k": [1, 2, 3],
    "PANCANCER_ATLAS": [1, 2, 3],
    "PATENTS":        [1, 2, 3],
    "stockindex":     [1, 2, 3],
    "stockmarket":    [1, 2, 3, 4, 5],
    "yelp":           [1, 2, 3, 4, 5, 6, 7],
}

ALL_DATASETS = list(DATASET_QUERIES.keys())


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                Path(__file__).parent.parent / "results" / "benchmark_run.log",
                encoding="utf-8",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------

def run_single(
    dataset: str,
    query_id: int,
    trial: int,
    llm: str,
    max_iterations: int,
    use_hints: bool,
    dab_root: Path,
    kb_root: Path,
    results_root: Path,
) -> dict:
    """Run one agent trial on one query. Returns the result dict."""
    logger = logging.getLogger("run_benchmark")
    logger.info(f"▶ {dataset}/q{query_id} trial {trial}  [{llm}]")

    try:
        agent = OracleAgent(
            dataset=dataset,
            query_id=query_id,
            deployment_name=llm,
            max_iterations=max_iterations,
            dab_root=dab_root,
            kb_root=kb_root,
            results_root=results_root,
            use_hints=use_hints,
        )
        result = agent.run()
    except FileNotFoundError as e:
        logger.error(f"  Skipping — {e}")
        result = {
            "dataset": dataset,
            "query_id": str(query_id),
            "answer": "",
            "terminate_reason": "dataset_not_found",
            "success": False,
            "duration_s": 0,
            "llm_calls": 0,
            "retries": 0,
            "timestamp": datetime.now().isoformat(),
            "trace_path": "",
        }

    result["run"] = trial
    icon = "✅" if result.get("success") else "❌"
    logger.info(
        f"  {icon} answer='{str(result.get('answer', ''))[:80]}' "
        f"reason={result.get('terminate_reason')} "
        f"llm_calls={result.get('llm_calls')} "
        f"duration={result.get('duration_s')}s"
    )
    return result


def run_benchmark(
    datasets: list[str],
    trials: int,
    llm: str,
    max_iterations: int,
    use_hints: bool,
    dab_root: Path,
    kb_root: Path,
    results_root: Path,
    output_file: Path,
) -> list[dict]:
    """Run full benchmark across datasets × queries × trials."""
    logger = logging.getLogger("run_benchmark")
    all_results: list[dict] = []

    total_queries = sum(len(DATASET_QUERIES.get(d, [])) for d in datasets)
    total_runs = total_queries * trials
    logger.info(
        f"Starting benchmark: {len(datasets)} datasets, "
        f"{total_queries} queries, {trials} trial(s) each = {total_runs} runs"
    )

    # Load existing results if resuming
    if output_file.exists():
        with open(output_file, encoding="utf-8") as f:
            all_results = json.load(f)
        logger.info(f"Resuming from {len(all_results)} existing results in {output_file}")

    completed = {
        (r["dataset"], str(r["query_id"]), str(r.get("run", 0)))
        for r in all_results
    }

    run_start = time.time()

    for dataset in datasets:
        query_ids = DATASET_QUERIES.get(dataset, [])
        for query_id in query_ids:
            for trial in range(trials):
                key = (dataset, str(query_id), str(trial))
                if key in completed:
                    logger.debug(f"  Skipping {key} (already done)")
                    continue

                result = run_single(
                    dataset=dataset,
                    query_id=query_id,
                    trial=trial,
                    llm=llm,
                    max_iterations=max_iterations,
                    use_hints=use_hints,
                    dab_root=dab_root,
                    kb_root=kb_root,
                    results_root=results_root,
                )
                all_results.append(result)

                # Save incrementally
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(all_results, f, indent=2)

    elapsed = time.time() - run_start
    successes = sum(1 for r in all_results if r.get("success"))
    logger.info(
        f"Benchmark complete in {elapsed:.1f}s | "
        f"{successes}/{len(all_results)} successful runs"
    )
    return all_results


def build_submission_json(results: list[dict], output: Path) -> None:
    """
    Build the leaderboard-format JSON:
    [{"dataset": ..., "query": ..., "run": ..., "answer": ...}, ...]
    """
    submission = [
        {
            "dataset": r["dataset"],
            "query": str(r["query_id"]),
            "run": str(r.get("run", 0)),
            "answer": r.get("answer", ""),
        }
        for r in results
    ]
    with open(output, "w", encoding="utf-8") as f:
        json.dump(submission, f, indent=2)
    logging.getLogger("run_benchmark").info(f"Submission JSON saved: {output}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Oracle Forge — DataAgentBench Runner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Target selection
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--all", action="store_true", help="Run all 12 datasets")
    target.add_argument("--datasets", nargs="+", choices=ALL_DATASETS, help="Specific datasets")
    parser.add_argument("--dataset", choices=ALL_DATASETS, help="Single dataset (use with --query_id)")
    parser.add_argument("--query_id", type=int, help="Single query ID")

    # Run config
    parser.add_argument("--llm", default="claude-opus-4-6", help="LLM deployment name")
    parser.add_argument("--trials", type=int, default=5, help="Trials per query")
    parser.add_argument("--max_iterations", type=int, default=100)
    parser.add_argument("--no_hints", action="store_true", help="Disable db_description hints")
    parser.add_argument("--log_level", default="INFO")

    # Paths
    _root = Path(__file__).parent.parent
    parser.add_argument("--dab_root", default=str(_root / "DataAgentBench"))
    parser.add_argument("--kb_root", default=str(_root / "kb"))
    parser.add_argument("--results_root", default=str(_root / "results"))
    parser.add_argument("--output", default=str(_root / "results" / "benchmark_results.json"))

    args = parser.parse_args()

    setup_logging(args.log_level)
    logger = logging.getLogger("run_benchmark")

    dab_root = Path(args.dab_root)
    kb_root = Path(args.kb_root)
    results_root = Path(args.results_root)
    results_root.mkdir(parents=True, exist_ok=True)
    output_file = Path(args.output)

    # ── Single query mode ──────────────────────────────────────────────
    if args.dataset and args.query_id:
        result = run_single(
            dataset=args.dataset,
            query_id=args.query_id,
            trial=0,
            llm=args.llm,
            max_iterations=args.max_iterations,
            use_hints=not args.no_hints,
            dab_root=dab_root,
            kb_root=kb_root,
            results_root=results_root,
        )
        print(json.dumps(result, indent=2))
        return

    # ── Multi-dataset mode ─────────────────────────────────────────────
    if args.all:
        datasets = ALL_DATASETS
    elif args.datasets:
        datasets = args.datasets
    else:
        parser.error("Specify --all, --datasets, or --dataset + --query_id")
        return

    results = run_benchmark(
        datasets=datasets,
        trials=args.trials,
        llm=args.llm,
        max_iterations=args.max_iterations,
        use_hints=not args.no_hints,
        dab_root=dab_root,
        kb_root=kb_root,
        results_root=results_root,
        output_file=output_file,
    )

    # Build submission JSON
    submission_path = output_file.parent / "submission.json"
    build_submission_json(results, submission_path)
    logger.info(f"Done. Results: {output_file} | Submission: {submission_path}")


if __name__ == "__main__":
    main()
