# Context Layers — Oracle Forge Implementation Mapping

**Injection test**: Ask "How do Oracle Forge's three context layers map to OpenAI's six layers?" → should answer with the table below mapping each Oracle Forge layer to its OpenAI equivalent.

## Mapping: OpenAI Six Layers → Oracle Forge Three Layers

| OpenAI Layer | Description | Oracle Forge Equivalent |
|---|---|---|
| 1. Global schema catalog | Names/descriptions of all tables | Layer 1: `db_description.txt` from DAB |
| 2. Relevant table enrichment | Codex-generated descriptions of likely tables | Layer 1: `db_description_withhint.txt` (hint-enriched) |
| 3. Column-level detail | Full column types + sample values | Layer 1: schema injected via `ContextManager.build()` |
| 4. Institutional knowledge | Business rules, fiscal calendar, join key formats | Layer 2: `kb/domain/` — join_keys, terminology, schemas |
| 5. Self-learning memory | Past successful query patterns | Layer 3: `kb/corrections/corrections_log.md` correct approaches |
| 6. Interaction history | User corrections, preferences | Layer 3: corrections log failure entries |

Oracle Forge collapses OpenAI's layers 1-3 into **Layer 1** (all schema information), layers 4 into **Layer 2** (domain KB), and layers 5-6 into **Layer 3** (corrections log). This is the minimum viable context architecture for DAB.

## How Layers Are Injected

```python
# agent/context_manager.py
ctx = ContextManager(kb_root="kb/", dab_root="DataAgentBench/")
system_addendum = ctx.build(dataset="yelp")
# → appended to base DataAgent system prompt before first LLM call
```

## Layer Priority Under Token Pressure

If context window fills up, truncate in this order (least important first):
1. Corrections log entries older than 7 days
2. Schema notes for datasets not relevant to current query
3. Architecture KB (only needed during development, not runtime)

**Never truncate**: join key glossary, current query's schema, recent corrections.

## Layer Update Frequency

| Layer | Updated when |
|---|---|
| Layer 1 (schema) | New dataset added or DB schema changes |
| Layer 2 (domain) | New join key pattern discovered, new terminology defined |
| Layer 3 (corrections) | After every failed agent run (automatic) |
