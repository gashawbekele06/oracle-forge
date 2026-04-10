# Corrections Log

Running log of agent failures and correct approaches.
Updated automatically by OracleAgent on failed runs; reviewed and annotated by Drivers.

---

**Format**:
```
**Dataset**: <name> | **Query**: <id>
**Query**: <first 300 chars of the query text>
**What went wrong**: <error or wrong approach>
**Correct approach**: <what should have been done>
```

---

## Seed Entries (from DAB paper failure analysis)

---
**Dataset**: crmarenapro | **Query**: cross-db join

**Query**: Which customers have open support tickets AND made a purchase in Q3?

**What went wrong**: Agent tried to JOIN `customers` (PostgreSQL) directly with `tickets` (DuckDB) in a single SQL query — this fails because they are different database systems.

**Correct approach**: Query `customers` from PostgreSQL, query `tickets` from DuckDB separately, then merge in execute_python after normalizing customer_id format (int vs "CUST-{padded}").

---
**Dataset**: crmarenapro | **Query**: ill-formatted join key

**Query**: Count customers who appear in both the CRM tickets and NPS scores tables.

**What went wrong**: Direct join on `customer_id` produced 0 results because DuckDB tickets use `"CUST-0001001"` format while PostgreSQL customers use integer `1001`.

**Correct approach**:
```python
df_tickets['cid_int'] = df_tickets['cid'].str.replace('CUST-', '').str.lstrip('0').astype(int)
merged = pd.merge(df_customers, df_tickets, left_on='customer_id', right_on='cid_int')
```

---
**Dataset**: yelp | **Query**: unstructured extraction

**Query**: How many reviews mention "wait time" as a complaint?

**What went wrong**: Agent used SQL `WHERE text LIKE '%wait%'` which returns rows mentioning "wait" in any context (including positive mentions). Count was 3x the correct answer.

**Correct approach**: Fetch all reviews, then in execute_python use multi-keyword regex:
```python
import re
WAIT_COMPLAINT = re.compile(r'(long wait|wait(?:ed|ing)? (too long|forever|hour))', re.I)
df['is_wait_complaint'] = df['text'].apply(lambda t: bool(WAIT_COMPLAINT.search(str(t))))
count = df['is_wait_complaint'].sum()
```

---
**Dataset**: stockmarket | **Query**: domain knowledge gap

**Query**: What is the average daily return for the top 10 stocks by volume in Q3 2024?

**What went wrong**: Agent computed return as `close / open - 1` (intraday return) instead of `(close_today - close_yesterday) / close_yesterday` (daily return).

**Correct approach**: Sort by date, compute `pct_change()` per ticker using pandas:
```python
df = df.sort_values(['ticker', 'date'])
df['daily_return'] = df.groupby('ticker')['close'].pct_change()
```


---
**Dataset**: yelp | **Query**: 1

**Query**: unknown

**What went wrong**: FatalError: MongoDB load error (FileNotFoundError): [Errno 2] No such file or directory: 'mongorestore'

**Correct approach**: [To be filled by team after manual diagnosis]


---
**Dataset**: yelp | **Query**: 3

**Query**: unknown

**What went wrong**: terminate_reason=llm_response_failed (APIStatusError): Error code: 402 - {'error': {'message': 'This request requires more credits, or fewer max_tokens. You requested up to 65536 tokens, but can only afford 30038. To increase, visit https://openrouter.ai/settings/keys and create a key with a higher weekly limit', 'code': 402, 'metadata': {'provider_name': None}}, 'user_id': 'org_3B7LqR6KG0MSzOr4fEskO8X8zKr'}, answer=''

**Correct approach**: [To be filled by team after manual diagnosis]


---
**Dataset**: yelp | **Query**: 4

**Query**: unknown

**What went wrong**: terminate_reason=llm_response_failed (APIStatusError): Error code: 402 - {'error': {'message': 'This request requires more credits, or fewer max_tokens. You requested up to 65536 tokens, but can only afford 30038. To increase, visit https://openrouter.ai/settings/keys and create a key with a higher weekly limit', 'code': 402, 'metadata': {'provider_name': None}}, 'user_id': 'org_3B7LqR6KG0MSzOr4fEskO8X8zKr'}, answer=''

**Correct approach**: [To be filled by team after manual diagnosis]
