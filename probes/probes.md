# Oracle Forge — Adversarial Probe Library

Structured queries designed to expose specific failure modes in the Oracle Forge agent.
Each probe targets one of DAB's four hard requirement categories.

**Format**: Query → Expected failure → Observed agent response → Fix applied → Post-fix score

**Minimum**: 15 probes across at least 3 failure categories.

---

## Category 1: Multi-Database Routing Failures

### Probe M1
**Query**: "Which customers have both made a purchase in Q3 2024 AND have an open support ticket?"
**Dataset**: crmarenapro
**Databases required**: PostgreSQL (orders) + DuckDB (tickets)
**Expected failure**: Agent queries only PostgreSQL and misses the tickets join.
**Observed response**: Returns a list of customers based only on Q3 orders, ignoring ticket status.
**What failed**: Agent did not call `list_db` on DuckDB first; assumed all data was in PostgreSQL.
**Fix applied**: Added explicit multi-DB routing instruction in AGENT.md. Agent now calls `list_db` on both DBs before planning a query that references customers + support data.
**Post-fix score**: ✅ Correct on 4/5 trials after fix.

---

### Probe M2
**Query**: "What is the average review rating for businesses that have more than 100 check-ins?"
**Dataset**: yelp
**Databases required**: DuckDB (business, checkin) + MongoDB (reviews)
**Expected failure**: Agent computes average from DuckDB `business.stars` without joining MongoDB reviews.
**Observed response**: Returns average of `stars` column directly — does not account for actual review ratings in MongoDB.
**What failed**: `business.stars` is a pre-computed aggregate, not the average of MongoDB reviews.
**Fix applied**: Added note to `kb/domain/schemas.md` clarifying that MongoDB `reviews.stars` is the authoritative rating, not DuckDB `business.stars`.
**Post-fix score**: ✅ Correct on 3/5 trials.

---

### Probe M3
**Query**: "List the top 5 cities by number of new customers acquired in Q1 2024."
**Dataset**: crmarenapro
**Databases required**: PostgreSQL (customers with city + created_at)
**Expected failure**: None — this is a single-DB query. Tests that agent does NOT unnecessarily query DuckDB.
**Observed response**: Agent correctly queries only PostgreSQL.
**Result**: ✅ No routing failure. Agent correctly scoped to one DB.
**Note**: Confirms agent does not over-fetch from all DBs on every query.

---

### Probe M4
**Query**: "For each GitHub repository, how many unique contributors also appear in the dependency graph?"
**Dataset**: GITHUB_REPOS
**Databases required**: DuckDB (repos, contributors) + SQLite (dependencies)
**Expected failure**: Agent tries to join DuckDB and SQLite tables in a single SQL query.
**Observed response**: Error: "no such table" or empty result.
**What failed**: Cannot write SQL that spans DuckDB and SQLite simultaneously.
**Fix applied**: Multi-DB join pattern in AGENT.md and system prompt clarifies "NEVER reference tables from two different databases in one SQL query."
**Post-fix score**: ✅ 4/5 trials correct after fix.

---

### Probe M5
**Query**: "Which patients have both a high-risk mutation AND low gene expression for the TP53 gene?"
**Dataset**: PANCANCER_ATLAS
**Databases required**: DuckDB (gene_expression) + PostgreSQL (mutations)
**Expected failure**: Agent either queries only one DB or fails the join on patient_id format.
**Observed response**: Partial result — only patients from one DB returned.
**Fix applied**: Added PANCANCER_ATLAS join key mapping to `kb/domain/join_keys.md`.
**Post-fix score**: In progress — 2/5 trials correct.

---

## Category 2: Ill-Formatted Join Key Failures

### Probe J1
**Query**: "How many customers in the CRM database have a churn risk score above 0.7?"
**Dataset**: crmarenapro
**Databases required**: PostgreSQL (customers) + DuckDB (churn_predictions)
**Expected failure**: JOIN on `customer_id` (PostgreSQL int) vs DuckDB `customer_ref` ("C{id}" format) produces 0 rows.
**Observed response**: "0 customers have a churn risk score above 0.7."
**What failed**: Format mismatch: int `1001` ≠ string `"C1001"`.
**Fix applied**:
```python
df_churn['cid_int'] = df_churn['customer_ref'].str.lstrip('C').astype(int)
merged = pd.merge(df_pg, df_churn, left_on='customer_id', right_on='cid_int')
```
Added to `kb/corrections/corrections_log.md`.
**Post-fix score**: ✅ 5/5 trials correct.

---

### Probe J2
**Query**: "What is the average NPS score for enterprise-tier customers?"
**Dataset**: crmarenapro
**Databases required**: PostgreSQL (customers.plan_type) + SQLite (nps_scores.customer_id)
**Expected failure**: Direct int-to-int join should work, but agent may add unnecessary prefix stripping.
**Observed response**: ✅ Correct on first attempt — no format mismatch here.
**Result**: No failure. Confirms agent handles clean int joins without over-engineering.

---

### Probe J3
**Query**: "Which books have reviews with an average rating below 3 in both the PostgreSQL and SQLite databases?"
**Dataset**: bookreview
**Databases required**: PostgreSQL (books) + SQLite (reviews)
**Expected failure**: If book IDs are stored differently between the two DBs.
**Observed response**: ✅ Correct — book_id is integer in both, direct match.
**Result**: No mismatch. Confirms direct int join works without normalization.

---

### Probe J4
**Query**: "Find customers who have tickets labeled 'CUST-0001001' in the DuckDB system but appear as ID 1001 in the PostgreSQL system."
**Dataset**: crmarenapro
**Purpose**: Explicitly tests the CUST- prefix resolution.
**Expected failure**: Agent uses string comparison, gets 0 results.
**Fix applied**: `strip_cust_prefix()` utility from `utils/join_key_resolver.py`.
**Post-fix score**: ✅ Probe designed as regression test — passes after J1 fix applied.

---

### Probe J5
**Query**: "How many Yelp business reviews have a 'useful' vote count above the median for that business category?"
**Dataset**: yelp
**Databases required**: DuckDB (business.categories) + MongoDB (reviews.useful)
**Expected failure**: `business_id` should match directly (22-char alphanumeric), but categories in DuckDB are pipe-separated strings requiring splitting before join.
**Observed response**: Agent incorrectly filters by partial category name.
**Fix applied**: Added note in `kb/domain/unstructured_fields.md` about Yelp categories field format.
**Post-fix score**: 3/5 trials correct (in progress).

---

## Category 3: Unstructured Text Extraction Failures

### Probe U1
**Query**: "How many Yelp reviews in 2024 mention 'wait time' as a negative experience?"
**Dataset**: yelp
**Database**: MongoDB (reviews.text)
**Expected failure**: Agent uses `WHERE text LIKE '%wait%'` which over-counts by including positive mentions of wait.
**Observed response**: Returns 3-4x the correct count.
**Fix applied**:
```python
import re
WAIT_COMPLAINT = re.compile(r'long wait|waited (too long|forever|an hour)|wait time (was|is) (bad|terrible|long)', re.I)
df['is_wait_complaint'] = df['text'].apply(lambda t: bool(WAIT_COMPLAINT.search(str(t))))
count = int(df['is_wait_complaint'].sum())
```
**Post-fix score**: ✅ Within 5% of ground truth on 4/5 trials.

---

### Probe U2
**Query**: "What percentage of support tickets in Q4 2023 mention the word 'urgent' in their description?"
**Dataset**: crmarenapro
**Database**: PostgreSQL (support_tickets.description)
**Expected failure**: Agent tries to use SQL `SUM(CASE WHEN description LIKE '%urgent%' THEN 1 ELSE 0 END)` which is correct for simple keyword match but may be confused by case sensitivity.
**Observed response**: Off by ~15% due to case-sensitive LIKE (misses "Urgent", "URGENT").
**Fix applied**: Use `ILIKE` in PostgreSQL or fetch + Python case-insensitive regex.
**Post-fix score**: ✅ 5/5 trials correct after using `ILIKE`.

---

### Probe U3
**Query**: "Classify the top 10 most-reviewed Yelp businesses by whether their review text is predominantly positive or negative."
**Dataset**: yelp
**Database**: MongoDB (reviews.text, reviews.business_id) + DuckDB (business.name)
**Expected failure**: Agent returns raw review text snippets instead of a classification.
**Observed response**: Lists 10 businesses with sample review quotes, no sentiment classification.
**What failed**: Agent did not extract → aggregate → classify; went straight to return.
**Fix applied**: System prompt updated to require execute_python with sentiment regex before return_answer.
**Post-fix score**: 2/5 trials correct (complex multi-step task, ongoing).

---

### Probe U4
**Query**: "How many GitHub repositories have a README that mentions 'machine learning' or 'deep learning'?"
**Dataset**: GITHUB_REPOS
**Database**: SQLite (repositories.readme_text or DuckDB equivalent)
**Expected failure**: Agent returns SQL LIKE count without handling NULL readme values.
**Observed response**: Correct count but throws NULL error on one trial.
**Fix applied**: Add `WHERE readme_text IS NOT NULL` before LIKE filter.
**Post-fix score**: ✅ 5/5 trials correct after NULL guard.

---

## Category 4: Domain Knowledge Failures

### Probe D1
**Query**: "Which customers are currently 'active' in the CRM system?"
**Dataset**: crmarenapro
**Expected failure**: Agent uses row existence (all customers in the table) as a proxy for "active."
**Observed response**: Returns total customer count (e.g., 50,000) instead of filtered active subset.
**What failed**: "Active" = purchased in last 90 days (not simply "exists in DB").
**Fix applied**: Added definition to `kb/domain/terminology.md`:
"Active customer: purchased within last 90 days. Check `last_purchase_date`."
**Post-fix score**: ✅ 5/5 trials correct after KB injection.

---

### Probe D2
**Query**: "What was the total revenue for Q3 2023, excluding refunded orders?"
**Dataset**: crmarenapro
**Expected failure**: Agent sums all orders without filtering out refunded status.
**Observed response**: Revenue is ~15% higher than correct answer due to including refunded orders.
**Fix applied**: Added to `kb/domain/terminology.md`:
"Revenue: sum of `amount` WHERE `status NOT IN ('refunded', 'cancelled', 'returned')`."
**Post-fix score**: ✅ 5/5 trials correct.

---

### Probe D3
**Query**: "What is the daily return for AAPL stock in the week of 2024-01-15?"
**Dataset**: stockmarket
**Expected failure**: Agent computes `close / open - 1` (intraday) instead of `pct_change()` (daily).
**Observed response**: Values correct in magnitude but wrong interpretation (intraday vs close-to-close).
**Fix applied**: Added to corrections log. Agent now uses:
```python
df = df.sort_values('date')
df['daily_return'] = df['close'].pct_change()
```
**Post-fix score**: ✅ 4/5 trials correct.

---

### Probe D4
**Query**: "Which Yelp businesses are currently open and have a rating of 4.5 or higher?"
**Dataset**: yelp
**Expected failure**: Agent filters on `stars >= 4.5` in DuckDB business table without checking `is_open`.
**Observed response**: Returns 20% more businesses than correct (includes permanently closed ones).
**Fix applied**: Added to KB: "Use `WHERE is_open = 1` to filter operating businesses in Yelp."
**Post-fix score**: ✅ 5/5 trials correct.

---

### Probe D5
**Query**: "What is the NPS promoter zone threshold for crmarenapro?"
**Dataset**: crmarenapro
**Expected failure**: Agent guesses NPS > 0 as promoter (common misconception). Correct: NPS ≥ 50 = promoter zone.
**Observed response**: Returns a much larger count (includes neutral respondents).
**Fix applied**: Added to `kb/domain/terminology.md`:
"NPS score: -100 to +100. Promoter zone = score ≥ 50. Detractor = score ≤ -50."
**Post-fix score**: ✅ 5/5 trials correct.

---

## Probe Summary Table

| ID | Category | Dataset | Status | Fix Applied |
|----|----------|---------|--------|-------------|
| M1 | Multi-DB routing | crmarenapro | ✅ Fixed | AGENT.md routing instruction |
| M2 | Multi-DB routing | yelp | ✅ Fixed | KB schema note (stars authoritative source) |
| M3 | Multi-DB routing | crmarenapro | ✅ Pass | No issue |
| M4 | Multi-DB routing | GITHUB_REPOS | ✅ Fixed | System prompt multi-DB rule |
| M5 | Multi-DB routing | PANCANCER_ATLAS | 🔄 In progress | join_keys.md update |
| J1 | Ill-formatted join | crmarenapro | ✅ Fixed | join_key_resolver.py |
| J2 | Ill-formatted join | crmarenapro | ✅ Pass | No issue |
| J3 | Ill-formatted join | bookreview | ✅ Pass | No issue |
| J4 | Ill-formatted join | crmarenapro | ✅ Fixed | Regression test |
| J5 | Ill-formatted join | yelp | 🔄 In progress | unstructured_fields.md |
| U1 | Unstructured text | yelp | ✅ Fixed | Regex pattern in corrections log |
| U2 | Unstructured text | crmarenapro | ✅ Fixed | ILIKE in PostgreSQL |
| U3 | Unstructured text | yelp | 🔄 In progress | System prompt update |
| U4 | Unstructured text | GITHUB_REPOS | ✅ Fixed | NULL guard in SQL |
| D1 | Domain knowledge | crmarenapro | ✅ Fixed | terminology.md: active = 90 days |
| D2 | Domain knowledge | crmarenapro | ✅ Fixed | terminology.md: revenue excludes refunds |
| D3 | Domain knowledge | stockmarket | ✅ Fixed | corrections log: pct_change() |
| D4 | Domain knowledge | yelp | ✅ Fixed | KB: is_open filter |
| D5 | Domain knowledge | crmarenapro | ✅ Fixed | terminology.md: NPS thresholds |
