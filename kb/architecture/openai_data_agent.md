# OpenAI In-House Data Agent — Six-Layer Context Architecture

**Injection test**: Ask "What is the hardest sub-problem in OpenAI's data agent?" → should answer "table enrichment across 70,000 tables."

## The Six Layers (Jan 2026 writeup)

OpenAI's production data agent uses six context layers injected before any user query:

1. **Global schema catalog** — names and descriptions of all 70,000+ tables.
2. **Relevant table enrichment** — Codex-powered descriptions of likely-relevant tables,
   generated fresh per query using the query text as a retrieval signal.
3. **Column-level detail** — full column names, types, and sample values for selected tables.
4. **Institutional knowledge** — business rules, fiscal calendar, status code meanings,
   join key formats (what the schema alone cannot tell you).
5. **Self-learning memory** — past successful query patterns and their SQL, indexed by topic.
6. **Interaction history** — corrections, user preferences, disambiguation resolutions.

## Key Insight: Table Enrichment Is the Hard Problem

With 70,000 tables, the agent cannot inject all schemas. Table enrichment solves this:
- For each incoming query, retrieve the 5-20 most relevant tables using semantic search.
- Then generate natural-language descriptions of those tables using Codex.
- Inject only the enriched descriptions (not raw schema dumps) into context.

**For Oracle Forge**: DAB has far fewer tables per dataset (2-27). Apply the same principle:
inject enriched descriptions (from `kb/domain/schemas.md`), not raw `DESCRIBE TABLE` output.

## Closed-Loop Self-Correction Pattern

```
query → plan → execute → validate output → 
  if fail: diagnose → patch context → re-execute (max 3 retries)
  if pass: return answer + log successful pattern
```

The agent never surfaces an error to the user. It diagnoses and retries internally.
Successful patterns are logged to the self-learning memory layer for future reuse.

## Application to Oracle Forge

Use three of the six layers (minimum spec):
- **Layer 1** (schema): DAB `db_description.txt` + hints
- **Layer 2** (institutional): `kb/domain/` documents
- **Layer 3** (corrections): `kb/corrections/corrections_log.md`

The self-correction loop is implemented in `agent/oracle_agent.py` as the retry mechanism.
