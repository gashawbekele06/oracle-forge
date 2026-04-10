# Domain Terminology — Business Terms Across DAB Datasets

**Injection test**: Ask "What does 'active customer' mean in crmarenapro?" → should answer "purchased in last 90 days."

## Universal Business Term Definitions

### Customer Activity
- **Active customer**: purchased or used the service within the last **90 days** from the query date.
  - Do NOT use row existence as a proxy for activity.
  - Check `last_purchase_date`, `last_transaction_date`, or `updated_at` column.
- **Churned customer**: no activity for **>180 days**.
- **Repeat customer**: has **≥2** distinct transactions or sessions.

### Revenue & Financial
- **Revenue**: sum of `total_price`, `amount`, or `revenue` columns (NOT including refunded orders).
  - Exclude rows where `status IN ('refunded', 'cancelled', 'returned')`.
- **Fiscal year**: January 1 – December 31 unless dataset documentation states otherwise.
- **Q1**: Jan–Mar, **Q2**: Apr–Jun, **Q3**: Jul–Sep, **Q4**: Oct–Dec.
- **GMV** (Gross Merchandise Value): total transaction value before returns and fees.

### Ratings & Reviews
- **Positive review**: `stars >= 4` (out of 5) in Yelp; `rating >= 4` in GoogleLocal.
- **Negative review**: `stars <= 2` in Yelp; `rating <= 2` in GoogleLocal.
- **Neutral review**: `stars == 3` / `rating == 3`.
- **Negative sentiment** in free text: words like "terrible", "worst", "avoid", "horrible",
  "poor", "disappointed", "never again". Use regex: `r'terrible|worst|avoid|horrible|poor|disappoint'`

### Support & CRM
- **Open ticket**: `status IN ('open', 'pending', 'in_progress', 'new')`.
- **Resolved ticket**: `status IN ('closed', 'resolved', 'done')`.
- **SLA breach**: ticket age > 48 hours with status still open.
- **Ticket volume**: count of tickets, NOT sum of any numeric field.

### Time Windows
- **Recent**: last 30 days from the query date unless specified.
- **YoY** (year-over-year): same period last year vs this year.
- **MoM** (month-over-month): previous month vs current month.

## Dataset-Specific Terminology

### crmarenapro
- `plan_type`: 'free' | 'basic' | 'pro' | 'enterprise' — NOT NULL
- `churn_risk_score`: float 0.0–1.0; ≥0.7 = high risk
- `nps_score`: -100 to +100; ≥50 = promoter zone

### yelp
- `stars`: 1.0–5.0 (float, can be non-integer in aggregations)
- `useful`, `funny`, `cool`: vote counts on reviews — can be 0 (NOT NULL)
- `is_open`: 1 = currently operating, 0 = permanently closed

### stockmarket / stockindex
- `close`: adjusted closing price
- `volume`: number of shares traded
- **Return**: `(close_today - close_yesterday) / close_yesterday`

### PANCANCER_ATLAS
- **Sample**: one biopsy from one patient (one row in the sample table)
- **Gene expression**: log2 TPM values; higher = more expressed
- **Mutation type**: 'SNP', 'DEL', 'INS', 'DNP', 'ONP', 'TNP'
