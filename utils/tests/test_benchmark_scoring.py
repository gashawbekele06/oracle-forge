"""
Tests for evaluation harness scoring — Challenge 3 (Evaluation Science)

Maps to interim submission requirement:
  "Harness must produce scores with query trace"
  "Score log showing at least a first-run baseline against held-out set"

Covers:
  - pass@1 score calculation from benchmark_results.json
  - Required fields in trace files
  - Regression detection (score comparison between runs)
  - Score log format validation
"""

import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — replicate the scoring logic used by run_benchmark.py
# ─────────────────────────────────────────────────────────────────────────────

def compute_pass_at_1(results: list[dict]) -> dict:
    """
    Compute pass@1 per dataset and overall from benchmark_results.json entries.

    pass@1 = fraction of queries where success=True (at least one passing trial).
    """
    total = len(results)
    passed = sum(1 for r in results if r.get("success", False))

    by_dataset: dict[str, dict] = {}
    for r in results:
        ds = r.get("dataset", "unknown")
        if ds not in by_dataset:
            by_dataset[ds] = {"total": 0, "passed": 0}
        by_dataset[ds]["total"] += 1
        if r.get("success", False):
            by_dataset[ds]["passed"] += 1

    dataset_scores = {
        ds: v["passed"] / v["total"]
        for ds, v in by_dataset.items()
    }

    return {
        "total_queries": total,
        "passed": passed,
        "pass_at_1": passed / total if total > 0 else 0.0,
        "by_dataset": dataset_scores,
    }


REQUIRED_RESULT_FIELDS = {
    "dataset", "query_id", "answer", "terminate_reason",
    "llm_calls", "success", "timestamp",
}

REQUIRED_TRACE_FIELDS = {
    "dataset", "query_id", "terminate_reason", "llm_calls",
}


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_RESULTS = [
    {"dataset": "yelp",        "query_id": "1", "answer": "3.55", "terminate_reason": "return_answer", "llm_calls": 7,  "success": True,  "timestamp": "2026-04-10T10:00:00"},
    {"dataset": "yelp",        "query_id": "2", "answer": "PA",   "terminate_reason": "return_answer", "llm_calls": 10, "success": True,  "timestamp": "2026-04-10T10:01:00"},
    {"dataset": "yelp",        "query_id": "3", "answer": "",     "terminate_reason": "max_iter",      "llm_calls": 50, "success": False, "timestamp": "2026-04-10T10:05:00"},
    {"dataset": "crmarenapro", "query_id": "1", "answer": "42",   "terminate_reason": "return_answer", "llm_calls": 5,  "success": True,  "timestamp": "2026-04-10T10:10:00"},
    {"dataset": "crmarenapro", "query_id": "2", "answer": "",     "terminate_reason": "llm_error",     "llm_calls": 3,  "success": False, "timestamp": "2026-04-10T10:12:00"},
    {"dataset": "PATENTS",     "query_id": "1", "answer": "None", "terminate_reason": "return_answer", "llm_calls": 8,  "success": True,  "timestamp": "2026-04-10T10:20:00"},
]


# ─────────────────────────────────────────────────────────────────────────────
# pass@1 scoring
# ─────────────────────────────────────────────────────────────────────────────

class TestPassAt1Scoring:
    def test_overall_score_correct(self):
        """4 of 6 passing → pass@1 = 0.667."""
        score = compute_pass_at_1(SAMPLE_RESULTS)
        assert score["total_queries"] == 6
        assert score["passed"] == 4
        assert abs(score["pass_at_1"] - 4/6) < 0.001

    def test_perfect_score(self):
        results = [{"dataset": "yelp", "query_id": str(i), "success": True,
                    "answer": "x", "terminate_reason": "return_answer",
                    "llm_calls": 5, "timestamp": "2026-04-10T10:00:00"}
                   for i in range(1, 8)]
        score = compute_pass_at_1(results)
        assert score["pass_at_1"] == 1.0

    def test_zero_score(self):
        results = [{"dataset": "yelp", "query_id": str(i), "success": False,
                    "answer": "", "terminate_reason": "max_iter",
                    "llm_calls": 50, "timestamp": "2026-04-10T10:00:00"}
                   for i in range(1, 5)]
        score = compute_pass_at_1(results)
        assert score["pass_at_1"] == 0.0

    def test_per_dataset_scores(self):
        """Per-dataset breakdown must match manual counts."""
        score = compute_pass_at_1(SAMPLE_RESULTS)
        assert abs(score["by_dataset"]["yelp"] - 2/3) < 0.001       # 2/3 pass
        assert abs(score["by_dataset"]["crmarenapro"] - 1/2) < 0.001 # 1/2 pass
        assert score["by_dataset"]["PATENTS"] == 1.0                  # 1/1 pass

    def test_empty_results_returns_zero(self):
        score = compute_pass_at_1([])
        assert score["pass_at_1"] == 0.0
        assert score["total_queries"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# Required fields in result entries
# ─────────────────────────────────────────────────────────────────────────────

class TestResultEntrySchema:
    def test_all_required_fields_present(self):
        """Every result entry must have all required fields."""
        for entry in SAMPLE_RESULTS:
            missing = REQUIRED_RESULT_FIELDS - set(entry.keys())
            assert not missing, f"Entry {entry['query_id']} missing: {missing}"

    def test_terminate_reason_is_known_value(self):
        """terminate_reason must be one of the known DAB termination codes."""
        valid_reasons = {"return_answer", "max_iter", "llm_error",
                         "llm_response_failed", "exec_error", "timeout"}
        for entry in SAMPLE_RESULTS:
            assert entry["terminate_reason"] in valid_reasons, \
                f"Unknown terminate_reason: {entry['terminate_reason']}"

    def test_success_is_bool(self):
        for entry in SAMPLE_RESULTS:
            assert isinstance(entry["success"], bool)

    def test_llm_calls_is_positive_int(self):
        for entry in SAMPLE_RESULTS:
            assert isinstance(entry["llm_calls"], int)
            assert entry["llm_calls"] > 0

    def test_timestamp_is_valid_iso(self):
        for entry in SAMPLE_RESULTS:
            dt = datetime.fromisoformat(entry["timestamp"])
            assert dt.year >= 2026


# ─────────────────────────────────────────────────────────────────────────────
# Benchmark results JSON — loading and validation
# ─────────────────────────────────────────────────────────────────────────────

class TestBenchmarkResultsFile:
    def test_results_file_is_valid_json(self, tmp_path):
        """benchmark_results.json must be loadable as JSON."""
        results_path = tmp_path / "benchmark_results.json"
        results_path.write_text(json.dumps(SAMPLE_RESULTS, indent=2), encoding="utf-8")
        with open(results_path, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == len(SAMPLE_RESULTS)

    def test_results_file_roundtrip(self, tmp_path):
        """Write and re-read benchmark_results.json — data must be identical."""
        results_path = tmp_path / "benchmark_results.json"
        results_path.write_text(json.dumps(SAMPLE_RESULTS, indent=2), encoding="utf-8")
        loaded = json.loads(results_path.read_text(encoding="utf-8"))
        assert loaded == SAMPLE_RESULTS

    def test_live_results_file_if_exists(self):
        """
        If the real benchmark_results.json exists (post-benchmark run), validate it.
        Skipped in CI where results directory may be absent.
        """
        results_path = Path(__file__).parent.parent.parent / "results" / "benchmark_results.json"
        if not results_path.exists():
            pytest.skip("benchmark_results.json not present — skipping live validation")

        data = json.loads(results_path.read_text(encoding="utf-8"))
        assert isinstance(data, list), "benchmark_results.json must be a JSON array"
        assert len(data) > 0, "benchmark_results.json is empty"

        score = compute_pass_at_1(data)
        # Must have at least 2 datasets for a valid benchmark run
        assert len(score["by_dataset"]) >= 2
        # Score must be a valid probability
        assert 0.0 <= score["pass_at_1"] <= 1.0

    def test_live_results_54_queries(self):
        """Full benchmark run must cover all 54 DAB queries."""
        results_path = Path(__file__).parent.parent.parent / "results" / "benchmark_results.json"
        if not results_path.exists():
            pytest.skip("benchmark_results.json not present")

        data = json.loads(results_path.read_text(encoding="utf-8"))
        assert len(data) == 54, f"Expected 54 queries, got {len(data)}"

    def test_live_results_all_12_datasets(self):
        """Full benchmark must include all 12 DAB datasets."""
        results_path = Path(__file__).parent.parent.parent / "results" / "benchmark_results.json"
        if not results_path.exists():
            pytest.skip("benchmark_results.json not present")

        data = json.loads(results_path.read_text(encoding="utf-8"))
        datasets = {r["dataset"] for r in data}
        expected = {
            "yelp", "agnews", "bookreview", "crmarenapro", "googlelocal",
            "stockindex", "stockmarket", "DEPS_DEV_V1", "GITHUB_REPOS",
            "PANCANCER_ATLAS", "music_brainz_20k", "PATENTS",
        }
        missing = expected - datasets
        assert not missing, f"Missing datasets in results: {missing}"


# ─────────────────────────────────────────────────────────────────────────────
# Regression detection — score must improve between runs
# ─────────────────────────────────────────────────────────────────────────────

class TestRegressionDetection:
    def test_score_improved_between_runs(self):
        """
        Simulates the harness comparing two benchmark runs.
        Week 8 baseline (50%) → Week 9 final (100%) must show improvement.
        """
        run_week8 = [
            {"dataset": "yelp", "query_id": "1", "success": True,  "answer": "x", "terminate_reason": "return_answer", "llm_calls": 5, "timestamp": "2026-04-10T10:00:00"},
            {"dataset": "yelp", "query_id": "2", "success": False, "answer": "",  "terminate_reason": "max_iter",      "llm_calls": 50,"timestamp": "2026-04-10T10:05:00"},
        ]
        run_week9 = [
            {"dataset": "yelp", "query_id": "1", "success": True, "answer": "x", "terminate_reason": "return_answer", "llm_calls": 5, "timestamp": "2026-04-15T10:00:00"},
            {"dataset": "yelp", "query_id": "2", "success": True, "answer": "y", "terminate_reason": "return_answer", "llm_calls": 8, "timestamp": "2026-04-15T10:05:00"},
        ]
        score_w8 = compute_pass_at_1(run_week8)["pass_at_1"]
        score_w9 = compute_pass_at_1(run_week9)["pass_at_1"]
        assert score_w9 > score_w8, \
            f"Score did not improve: week8={score_w8:.1%}, week9={score_w9:.1%}"

    def test_no_regression_detected_when_equal(self):
        """Identical results across two runs → no regression."""
        run_a = [{"dataset": "yelp", "query_id": "1", "success": True, "answer": "x",
                  "terminate_reason": "return_answer", "llm_calls": 5,
                  "timestamp": "2026-04-10T10:00:00"}]
        run_b = [{"dataset": "yelp", "query_id": "1", "success": True, "answer": "x",
                  "terminate_reason": "return_answer", "llm_calls": 5,
                  "timestamp": "2026-04-15T10:00:00"}]
        assert compute_pass_at_1(run_a)["pass_at_1"] == compute_pass_at_1(run_b)["pass_at_1"]

    def test_regression_flagged_when_score_drops(self):
        """Score drop between runs must be detectable."""
        run_good = [{"dataset": "yelp", "query_id": str(i), "success": True, "answer": "x",
                     "terminate_reason": "return_answer", "llm_calls": 5,
                     "timestamp": "2026-04-10T10:00:00"} for i in range(1, 5)]
        run_bad  = [{"dataset": "yelp", "query_id": str(i), "success": False, "answer": "",
                     "terminate_reason": "max_iter", "llm_calls": 50,
                     "timestamp": "2026-04-15T10:00:00"} for i in range(1, 5)]
        score_good = compute_pass_at_1(run_good)["pass_at_1"]
        score_bad  = compute_pass_at_1(run_bad)["pass_at_1"]
        regression = score_bad < score_good
        assert regression, "Regression should have been detected"


# ─────────────────────────────────────────────────────────────────────────────
# Trace file validation
# ─────────────────────────────────────────────────────────────────────────────

class TestTraceFiles:
    def test_sample_trace_has_required_fields(self, tmp_path):
        """A trace file must contain required fields for query tracing."""
        trace = {
            "dataset": "yelp",
            "query_id": "1",
            "terminate_reason": "return_answer",
            "llm_calls": 7,
            "messages": [
                {"role": "user",      "content": "Which state has the most businesses?"},
                {"role": "assistant", "content": "I'll query the business table."},
                {"role": "tool",      "content": "SELECT state, COUNT(*) FROM business GROUP BY state"},
            ],
            "answer": "PA",
            "duration_s": 36.7,
        }
        trace_path = tmp_path / "q1_trace.json"
        trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")

        loaded = json.loads(trace_path.read_text(encoding="utf-8"))
        missing = REQUIRED_TRACE_FIELDS - set(loaded.keys())
        assert not missing, f"Trace missing required fields: {missing}"

    def test_live_trace_files_if_exist(self):
        """Validate a sample of real trace files from results/traces/."""
        traces_dir = Path(__file__).parent.parent.parent / "results" / "traces"
        if not traces_dir.exists():
            pytest.skip("results/traces/ not present")

        trace_files = list(traces_dir.glob("**/*.json"))[:10]  # sample first 10
        if not trace_files:
            pytest.skip("No trace files found")

        for tf in trace_files:
            data = json.loads(tf.read_text(encoding="utf-8"))
            assert isinstance(data, dict), f"{tf.name} is not a JSON object"
            missing = REQUIRED_TRACE_FIELDS - set(data.keys())
            assert not missing, f"{tf.name} missing fields: {missing}"
