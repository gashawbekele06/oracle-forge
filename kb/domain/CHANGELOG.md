# Domain KB — CHANGELOG

## v2 — 2026-04-10 (current)
- Added `join_keys.md`: Cross-database join key formats for yelp, bookreview, crmarenapro, agnews, googlelocal
- Added `terminology.md`: Universal business term definitions + dataset-specific terms
- Added `unstructured_fields.md`: Inventory of all free-text fields + extraction patterns
- Added `schemas.md`: Key table/collection schema notes and gotchas per dataset

**Injection tests**: All documents passed injection test on 2026-04-10.
**Test questions and expected answers**:
- "How is customer_id formatted in crmarenapro DuckDB?" → "CUST-{7-digit-padded}"
- "What is an active customer?" → "purchased within last 90 days"
- "Which yelp field contains review text?" → "`text` in MongoDB `reviews` collection"
- "What is the primary key in yelp DuckDB business table?" → "`business_id` (22-char str)"

## v1 — 2026-04-09
- Initial stub files created
