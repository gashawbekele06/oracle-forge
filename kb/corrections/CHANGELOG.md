# Corrections Log KB — CHANGELOG

## v3 — (updated continuously during sprint)
- Corrections appended automatically by OracleAgent after failed runs.
- Drivers annotate with "Correct approach" after manual diagnosis.

## v1 — 2026-04-10
- Added seed entries from DAB paper failure analysis:
  - Cross-DB join (wrong: single SQL; correct: separate queries + pandas merge)
  - Ill-formatted join key (wrong: direct join; correct: normalize "CUST-" prefix)
  - Unstructured extraction (wrong: SQL LIKE; correct: Python regex after fetch)
  - Domain knowledge gap (wrong: intraday return; correct: daily pct_change)
