# Schema Notes — Key Tables and Gotchas

**Injection test**: Ask "What is the primary key of the Yelp businesses table?" → should answer "`business_id` (22-char alphanumeric string)."

## General Schema Rules Across DAB

1. **Always call `list_db` first** on any dataset you haven't queried in this session.
2. **PostgreSQL**: column names with uppercase or spaces MUST be double-quoted in SQL.
   Example: `SELECT "CustomerID" FROM customers` (not `SELECT CustomerID FROM customers`).
3. **DuckDB**: supports analytical SQL extensions — use `MEDIAN()`, `PERCENTILE_CONT()`,
   `PIVOT`, and `UNNEST` freely. Does NOT require quoting lowercase names.
4. **MongoDB**: always specify `collection` key in query JSON.
   Aggregation pipeline: `[{"$match": {...}}, {"$group": {...}}, {"$sort": {...}}]`
5. **SQLite**: no native `MEDIAN` — use `percentile` from extension or compute in Python.
   DATE functions: use `strftime('%Y', date_col)` for year extraction.

## Yelp Dataset

**DuckDB** (`yelp_db`):
- `business`: `business_id` (PK, 22-char str), `name`, `city`, `state`, `stars`, `review_count`, `is_open`
- `tip`: `business_id` (FK), `user_id`, `date`, `text`, `compliment_count`
- `checkin`: `business_id` (FK), `date` (comma-separated datetime string — split before use)

**MongoDB** (`yelp_mongo`):
- `reviews`: `business_id`, `user_id`, `stars`, `date`, `text`, `useful`, `funny`, `cool`
- `users`: `user_id`, `name`, `review_count`, `yelping_since`, `fans`, `average_stars`

## CRMarenaPro Dataset

**PostgreSQL** (`crm_pg`):
- `customers`: `customer_id` (PK int), `name`, `email`, `plan_type`, `created_at`, `last_purchase_date`
- `products`: `product_id` (PK int), `name`, `category`, `price`
- `orders`: `order_id` (PK int), `customer_id` (FK), `product_id` (FK), `amount`, `status`, `created_at`

**DuckDB** (`crm_duck`):
- `tickets`: `ticket_id` (PK), `cid` ("CUST-{7-digit-padded}" FK to `customers.customer_id`), `description`, `status`, `created_at`
- `interactions`: `id` (PK), `customer_ref` ("C{id}" FK), `notes`, `outcome`, `date`

**SQLite** (`crm_sqlite`):
- `nps_scores`: `customer_id` (int FK), `score` (int -100 to 100), `recorded_at`
- `churn_predictions`: `customer_id` (int FK), `churn_risk_score` (float 0-1), `predicted_at`

## BookReview Dataset

**PostgreSQL** (`books_pg`):
- `books`: `book_id` (PK int), `title`, `author`, `genre`, `published_year`, `avg_rating`

**SQLite** (`books_sqlite`):
- `reviews`: `review_id` (PK), `book_id` (FK int), `reviewer`, `rating` (1-5), `review_text`, `date`

## StockMarket Dataset

**DuckDB** (`stock_duck`):
- `prices`: `ticker` (str), `date` (DATE), `open`, `high`, `low`, `close`, `volume`, `adj_close`
- 2754 tickers — always filter by ticker before aggregating.

**SQLite** (`stock_sqlite`):
- `metadata`: `ticker` (PK), `company_name`, `sector`, `industry`, `market_cap`
