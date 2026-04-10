# DAB Evaluation Guide — Scoring, Submission, and Failure Analysis

**Injection test**: Ask "What is the DAB scoring metric?" → should answer "pass@1 over 5 trials."

## Scoring Method: pass@1

DAB uses **pass@1** (also called "majority vote accuracy"):
- Run the agent on each query **n ≥ 5 times** (trials).
- For each query: the agent **passes** if at least one trial returns the correct answer.
- **pass@1 = (queries with at least 1 correct answer) / (total queries)**

The overall benchmark score is the average pass@1 across all 54 queries.

**Current leaderboard best** (April 2026): PromptQL (Gemini-3.1-Pro) = 0.543

## Answer Validation

The validation script compares agent answers to ground truth using:
1. **Exact match** for categorical answers (e.g., names, statuses)
2. **Numeric match ±1%** for numerical answers (e.g., counts, averages)
3. **Set match** for list answers (order-independent)

Location: `DataAgentBench/common_scaffold/validate/validate.py`

## The Four DAB Failure Categories

| Category | Failure type | Detection signal |
|---|---|---|
| Multi-database routing | Agent queries only one DB; misses cross-DB join | Missing data in result; agent returns partial answer |
| Ill-formatted join keys | Join produces 0 rows or wrong rows | Result count is 0 or wildly wrong number |
| Unstructured text extraction | Agent returns raw text instead of extracted fact | Answer is a paragraph, not a number or name |
| Domain knowledge gap | Agent uses naive proxy for business term | Answer is wrong but plausible; doesn't match ground truth |

## Submission Format

```json
[
  {
    "dataset": "yelp",
    "query": "1",
    "run": "0",
    "answer": "4.23"
  },
  ...
]
```

- Include **all trials** (run 0 through n-1) for every query.
- Missing runs → submission rejected.
- File: `results/submission.json`
- Submit via GitHub PR to `ucbepic/DataAgentBench`.

## Score Log Schema (Oracle Forge Harness)

```json
{
  "timestamp": "2026-04-10T12:00:00",
  "dataset": "yelp",
  "query_id": "1",
  "trial": 0,
  "answer": "4.23",
  "ground_truth": "4.21",
  "is_correct": true,
  "terminate_reason": "return_answer",
  "llm_calls": 6,
  "duration_s": 42.1,
  "retries": 0
}
```

## Running the Oracle Forge Evaluation Harness

```bash
# Score results against ground truth
python eval/score.py --results results/benchmark_results.json

# Full evaluation report
python eval/run_eval.py --results results/benchmark_results.json

# Expected output:
# Overall pass@1: 0.XX
# By dataset: yelp=0.XX, bookreview=0.XX, ...
# By failure category: routing=X/X, join_keys=X/X, ...
```
