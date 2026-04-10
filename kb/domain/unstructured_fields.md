# Unstructured Field Inventory

**Injection test**: Ask "Which field in the Yelp dataset contains free text that needs extraction?" → should answer "`text` field in the `reviews` collection."

## What Is an Unstructured Field

An unstructured field stores human-written text (reviews, notes, descriptions, comments)
rather than structured values. To use these fields in calculations, you must extract
structured facts from them first using Python — NOT in a SQL/MongoDB query.

## Pattern: Extract Then Aggregate

```
Step 1 → query_db: fetch raw text field rows (limit to relevant subset)
Step 2 → execute_python: extract structured fact (count, flag, score)
Step 3 → execute_python: aggregate extracted facts
Step 4 → return_answer: final result
```

## Known Unstructured Fields by Dataset

### yelp
| DB | Table/Collection | Field | What to extract |
|---|---|---|---|
| MongoDB | `reviews` | `text` | sentiment flags, keyword counts, mention of specific topics |
| MongoDB | `businesses` | `categories` | pipe-separated category list → split and filter |

**Extraction example** (sentiment from yelp reviews):
```python
import re
NEG_PATTERN = re.compile(r'terrible|worst|avoid|horrible|disappoint|never return', re.I)
df['is_negative'] = df['text'].apply(lambda t: bool(NEG_PATTERN.search(str(t))))
neg_count = df['is_negative'].sum()
```

### crmarenapro
| DB | Table | Field | What to extract |
|---|---|---|---|
| PostgreSQL | `support_tickets` | `description` | issue type, mentioned product, resolution keyword |
| DuckDB | `interactions` | `notes` | outcome flag ('resolved', 'escalated', 'pending') |

**Extraction example** (ticket severity from description):
```python
HIGH_KEYWORDS = re.compile(r'urgent|critical|down|outage|broken|cannot access', re.I)
df['is_high_severity'] = df['description'].apply(lambda t: bool(HIGH_KEYWORDS.search(str(t))))
```

### bookreview
| DB | Table | Field | What to extract |
|---|---|---|---|
| SQLite | `reviews` | `review_text` | sentiment, mentioned topics, author references |

### agnews
| DB | Collection | Field | What to extract |
|---|---|---|---|
| MongoDB | `articles` | `content` | entity mentions, topic classification, word counts |

**Extraction example** (word count):
```python
df['word_count'] = df['content'].apply(lambda t: len(str(t).split()))
```

### PATENTS
| DB | Table | Field | What to extract |
|---|---|---|---|
| SQLite | `publications` | `abstract` | technology domain keywords, claim counts |
| PostgreSQL | `claims` | `claim_text` | independent vs dependent claim classification |

## Important Rules

1. **Never** try to do text extraction inside a SQL query with LIKE patterns for counting.
   SQL LIKE is for filtering rows, not for extracting structured values.
2. **Always** fetch the raw text first with query_db, then process in execute_python.
3. Limit initial fetch to rows you need (use WHERE clauses to pre-filter by date/category).
4. For very large text fields, sample first: `LIMIT 1000` then extrapolate if necessary.
