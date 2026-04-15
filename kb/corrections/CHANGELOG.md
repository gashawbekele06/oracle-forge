# Corrections Log KB — CHANGELOG

## v3 — (updated continuously during sprint)
- Corrections appended automatically by OracleAgent after failed runs.
- Drivers annotate with "Correct approach" after manual diagnosis.
- PATENTS entries annotated with root cause (missing 5.42 GB DB file).

## v2 — 2026-04-10
- Runtime corrections appended from benchmark run (yelp, stockmarket, PATENTS failures).

## v1 — 2026-04-10
- Added seed entries from DAB paper failure analysis:
  - Cross-DB join (wrong: single SQL; correct: separate queries + pandas merge)
  - Ill-formatted join key (wrong: direct join; correct: normalize "CUST-" prefix)
  - Unstructured extraction (wrong: SQL LIKE; correct: Python regex after fetch)
  - Domain knowledge gap (wrong: intraday return; correct: daily pct_change)

**Injection tests — questions and expected answers (verified 2026-04-10)**:

| Test question | Expected answer | Result |
|---|---|---|
| "A cross-DB join returns 0 rows. What should the agent check first?" | Whether join key formats match — e.g., PostgreSQL integer vs DuckDB CUST- prefix; normalise before joining | ✅ Pass |
| "The agent used SQL LIKE '%slow%' on a review text field and got wrong results. What is the correct approach?" | Fetch the text field, then apply regex in execute_python — SQL LIKE cannot handle complex patterns | ✅ Pass |
| "PATENTS queries fail with db_path does not exist. What is the fix?" | Download patent_publication.db (5.42 GB) via download.sh with gdown retry loop | ✅ Pass |
| "What is the correct way to compute daily return in the stockmarket dataset?" | df.groupby('ticker')['close'].pct_change() — not a single SQL expression | ✅ Pass |
