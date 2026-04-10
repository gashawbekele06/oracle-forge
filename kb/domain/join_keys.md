# Join Key Glossary — Cross-Database Format Reference

**Injection test**: Ask "How is the customer identifier formatted in the Yelp DuckDB vs MongoDB?" → should answer with the format strings below.

## Why Join Keys Break

Enterprise databases evolve independently. The same entity appears with different ID formats:
- Integer PK in the transactional DB → string prefixed key in the CRM
- UUID in PostgreSQL → ObjectId in MongoDB
- Padded zero integer in SQLite → bare integer in DuckDB

The agent must detect and resolve these before attempting a join.

## Known Format Patterns Across DAB Datasets

### yelp
| Database | Table/Collection | Key field | Format | Example |
|---|---|---|---|---|
| DuckDB (`yelp_db`) | `business` | `business_id` | 22-char alphanumeric | `"iCQpiavjjPzJ5_3gPD5Eq"` |
| MongoDB (`yelp_mongo`) | `reviews` | `business_id` | Same 22-char format | `"iCQpiavjjPzJ5_3gPD5Eq"` |
| MongoDB (`yelp_mongo`) | `users` | `user_id` | 22-char alphanumeric | `"Ha3iJu77CxlrFm-vQRs_8g"` |

**Note**: Yelp join keys match directly — no transformation needed.

### bookreview
| Database | Table | Key field | Format | Example |
|---|---|---|---|---|
| PostgreSQL | `books` | `book_id` | Integer | `12345` |
| SQLite | `reviews` | `book_id` | Integer | `12345` |

**Note**: Direct integer match. No transformation needed.

### crmarenapro
| Database | Table | Key field | Format | Example |
|---|---|---|---|---|
| PostgreSQL | `customers` | `customer_id` | Integer | `1001` |
| DuckDB | `tickets` | `cid` | `"CUST-{integer}"` padded to 7 digits | `"CUST-0001001"` |
| SQLite | `interactions` | `customer_ref` | `"C{integer}"` | `"C1001"` |

**Resolution**: Strip `"CUST-"` prefix and leading zeros; strip `"C"` prefix. Cast to int for join.
```python
df['cid_int'] = df['cid'].str.replace('CUST-', '').str.lstrip('0').astype(int)
df['customer_ref_int'] = df['customer_ref'].str.lstrip('C').astype(int)
```

### agnews
| Database | Collection/Table | Key field | Format |
|---|---|---|---|
| MongoDB | `articles` | `article_id` | ObjectId string (24 hex chars) |
| SQLite | `categories` | `article_id` | Same 24-char hex string |

**Note**: Direct string match if both retrieved as strings.

### googlelocal
| Database | Table | Key field | Format | Example |
|---|---|---|---|---|
| PostgreSQL | `places` | `gmap_id` | `"0x{hex}:{hex}"` | `"0x89c259f0a4d4a2a1:0xa5d3d9e76fb5c0c3"` |
| SQLite | `reviews` | `gmap_id` | Same format | same |

**Note**: Direct string match. Ensure consistent quoting.

## Resolution Code Template

```python
import pandas as pd

def normalize_customer_id(series: pd.Series, prefix: str = "CUST-") -> pd.Series:
    """Strip prefix and leading zeros, return as int-compatible string."""
    if prefix:
        series = series.str.replace(prefix, "", regex=False)
    return series.str.lstrip("0").fillna("0")

def join_cross_db(df_a: pd.DataFrame, df_b: pd.DataFrame,
                  col_a: str, col_b: str,
                  norm_a=None, norm_b=None) -> pd.DataFrame:
    """Join two dataframes after optional key normalization."""
    if norm_a: df_a = df_a.copy(); df_a[col_a] = norm_a(df_a[col_a])
    if norm_b: df_b = df_b.copy(); df_b[col_b] = norm_b(df_b[col_b])
    return pd.merge(df_a, df_b, left_on=col_a, right_on=col_b)
```
