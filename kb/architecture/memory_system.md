# Memory System Design — Session and Persistent Memory

**Injection test**: Ask "What is the difference between session memory and persistent memory in Oracle Forge?" → should answer "Session memory is the agent's message history within one run; persistent memory is the corrections log and KB documents that survive across runs."

## Two Memory Types

### Session Memory (ephemeral)
- The LLM's message history within a single `DataAgent.run()` call.
- Contains: system prompt, tool calls, tool results, assistant reasoning.
- Lost when the run ends.
- Limit: the LLM's context window (~200k tokens for Claude Opus-4.6).
- Managed by: DataAgentBench `DataAgent.messages` list.

### Persistent Memory (survives across runs)
- Stored on disk; loaded fresh at the start of every run.
- Three components:
  1. **KB documents** (`kb/architecture/`, `kb/domain/`, `kb/evaluation/`): manually curated, updated when new knowledge is discovered.
  2. **Corrections log** (`kb/corrections/corrections_log.md`): automatically appended after failed runs; read at session start.
  3. **Benchmark results** (`results/benchmark_results.json`): score history for regression detection.

## autoDream Equivalent — KB Maintenance Protocol

Claude Code uses an automated `autoDream` process to consolidate memory. Oracle Forge uses a **manual equivalent**:

1. After every 10 benchmark runs, Intelligence Officers review `corrections_log.md`.
2. Recurring patterns → promoted to `kb/domain/` documents (more prominent injection position).
3. One-off errors → kept in corrections log.
4. Contradicted entries → removed from corrections log (append-only rule waived for corrections).

## Self-Learning Loop

```
Agent fails on query X
  → OracleAgent.run() catches failure
  → ContextManager.append_correction() writes entry to corrections_log.md
  → Next run of query X loads the correction in Layer 3
  → Agent avoids the same mistake
  → pass@1 score improves
```

This loop is the primary mechanism by which Oracle Forge improves between Week 8 and Week 9 without any model changes.

## Memory Capacity Limits

| Memory type | Limit | Current size |
|---|---|---|
| corrections_log.md | No hard limit; aim for <200 entries | ~10 entries |
| KB domain docs | Max 400 words each (Karpathy rule) | Compliant |
| Session message history | LLM context window | Managed by DAB scaffold |
