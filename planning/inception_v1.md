# AI-DLC Inception Document — Sprint 1
**Oracle Forge: Production Data Analytics Agent**
**Date**: April 10, 2026 | **Status**: Approved at mob session

---

## Press Release (What We Built)

The Oracle Forge team has delivered a production-grade natural language data analytics agent that answers complex business questions across heterogeneous enterprise databases. The agent handles multi-database queries spanning PostgreSQL, MongoDB, SQLite, and DuckDB simultaneously — the four systems used in the DataAgentBench benchmark. It applies a three-layer context architecture (schema knowledge, domain KB, corrections log) to achieve verifiable, auditable answers with measurable improvement between runs. The agent has been evaluated against 54 real-world enterprise data queries and submitted to the public DAB leaderboard, placing it in the top tier of open-source data agents.

---

## Honest FAQ — User Perspective

**Q1: Can I ask it any question about any database?**
A: No. The agent works against the 12 DataAgentBench datasets loaded into the Docker environment. It cannot connect to arbitrary external databases without configuration changes to `db_config.yaml` and the Docker Compose file.

**Q2: How long does a query take?**
A: Between 20 seconds and 5 minutes depending on query complexity and number of database lookups. Queries requiring large data fetches from MongoDB or DuckDB take longer. The agent will not time out before 10 minutes.

**Q3: Are the answers reliable?**
A: Reliability varies by query type. Single-database factual queries (counts, averages) are highly reliable. Cross-database joins and queries requiring unstructured text extraction are harder — the agent self-corrects up to 2 times, but some queries still fail. The evaluation harness measures exactly which queries pass and fail.

---

## Honest FAQ — Technical Perspective

**Q4: What is the hardest technical problem?**
A: Multi-database join key resolution. Enterprise databases independently evolve their ID formats — the same customer appears as integer `1001` in PostgreSQL and `"CUST-0001001"` in DuckDB. The agent must detect this mismatch and resolve it before attempting a join, without being told explicitly. Our `utils/join_key_resolver.py` handles known formats; unknown formats require the agent to sample rows and detect the pattern.

**Q5: What happens if the LLM generates incorrect SQL?**
A: The agent catches database execution errors and attempts up to 2 self-correction retries. Each retry includes a diagnostic hint injected into the context. If all retries fail, the failure is logged to `kb/corrections/corrections_log.md` for manual review and future correction. The evaluation harness records the failure category.

**Q6: How does the agent improve between Week 8 and Week 9?**
A: Through the corrections log (Layer 3 context). After each failed run, a correction entry is appended to `corrections_log.md`. At the start of every subsequent run, this log is injected into the agent context, giving it knowledge of past failures and correct approaches. The evaluation harness tracks the pass@1 score over time to confirm improvement.

---

## Key Decisions

1. **Claude claude-opus-4-6 as default model** (via Anthropic API or OpenRouter): Claude Opus-4.6 holds the #3 solo-agent position on the DAB leaderboard (0.4376 pass@1). We chose it over GPT-4o because of its stronger tool-use reliability on multi-step database queries.

2. **DataAgentBench scaffold as the agent foundation** (not a rewrite): The DAB repo provides battle-tested tool implementations (QueryDBTool, ExecTool, etc.) with existing support for all four database types. We extend it with the 3-layer context manager rather than replacing it, saving significant engineering time while maintaining compatibility with the DAB evaluation harness.

3. **Docker Compose for all services** (not local installation): All databases (PostgreSQL, MongoDB) run in containers. This ensures reproducibility across team members' machines and avoids the version/permission issues endemic to local DB installations.

---

## Definition of Done

The sprint is complete when all of the following are verifiably true:

1. `docker compose up` starts PostgreSQL and MongoDB without errors and passes healthchecks.
2. `python agent/run_benchmark.py --dataset yelp --query_id 1 --llm claude-opus-4-6` returns a non-empty answer within 5 minutes.
3. The agent handles at least two DAB database types (e.g., DuckDB + MongoDB for Yelp, PostgreSQL + SQLite for BookReview) with correct multi-DB join results.
4. `python eval/score.py --results results/benchmark_results.json` produces a pass@1 score ≥ 0.10.
5. The evaluation harness (`eval/run_eval.py`) produces a score log with at least two entries showing measurable improvement.
6. The `kb/corrections/corrections_log.md` has at least 4 entries from actual agent failures (beyond the seed entries).
7. The adversarial probe library (`probes/probes.md`) has at least 15 probes across at least 3 failure categories, with fix documentation.
8. A GitHub PR has been opened to `ucbepic/DataAgentBench` with the submission JSON.

---

## Mob Session Approval Record

**Date**: April 10, 2026
**Attendees**: All 6 team members present
**Hardest question asked**: "The definition of done says 'non-empty answer' for item 2 — but a wrong non-empty answer would also pass. How do we verify correctness?"
**Answer given**: Item 4 specifically requires pass@1 ≥ 0.10 against ground truth. Item 2 is a liveness check (agent runs without crashing), not a correctness check. The combination of items 2 + 4 covers both.
**Approval**: ✅ Full team approved. Construction phase begins.
