# Oracle Forge — Shared Utility Library

Reusable modules for any team member. All modules are documented, tested, and importable from the project root.

## Modules

### `join_key_resolver.py`
Detects and resolves join key format mismatches across heterogeneous databases.

**Use when**: merging results from two databases where the same entity has different ID formats (e.g., integer vs "CUST-0001001").

```python
from utils.join_key_resolver import resolve_join, JoinKeyResolver, detect_format

# Auto-detect format and merge
merged = resolve_join(df_postgres, 'customer_id', df_duckdb, 'cid')

# Inspect detected format
fmt = detect_format(df_duckdb['cid'])  # → 'cust_prefix'

# Full control
resolver = JoinKeyResolver(df_a, 'id', df_b, 'ref_id', how='left')
print(resolver.describe())  # → "JoinKeyResolver: 'id' (fmt=integer) ⟷ 'ref_id' (fmt=cust_prefix)"
merged = resolver.resolve_and_merge()
```

---

### `schema_introspection.py`
Programmatic schema discovery for PostgreSQL, MongoDB, SQLite, DuckDB.

**Use when**: the KB domain schemas are incomplete, or a new dataset is added.

```python
from utils.schema_introspection import SchemaInspector

inspector = SchemaInspector("DataAgentBench/query_yelp/db_config.yaml")
print(inspector.describe_all())
# → [yelp_db] DuckDB — file: ...
#      TABLE business (150,346 rows): business_id (VARCHAR), name (VARCHAR), ...
#   [yelp_mongo] MongoDB — database: yelp
#      COLLECTION reviews (6,990,280 docs): business_id, user_id, stars, ...
```

---

### `multi_pass_retrieval.py`
Multi-pass corrections log retrieval with vocabulary expansion.

**Use when**: searching the corrections log for relevant past failures before retrying a query.

```python
from utils.multi_pass_retrieval import MultiPassRetriever

retriever = MultiPassRetriever("kb/corrections/corrections_log.md")

# Returns top-5 relevant corrections with expanded vocabulary
results = retriever.search("customer id mismatch between postgres and duckdb")
print(retriever.format_results(results))
```

---

## Running Tests

```bash
# From project root
python -m pytest utils/tests/ -v

# Individual module
python -m pytest utils/tests/test_join_key_resolver.py -v
```

## Adding a New Utility

1. Create `utils/your_module.py` with docstring, usage example, type hints.
2. Add a test in `utils/tests/test_your_module.py`.
3. Update this README.
4. Run `python -m pytest utils/tests/` to confirm all tests pass.
