# Oracle Forge — Production Data Analytics Agent

> **TRP1 Week 8–9 Challenge · Arc 4: Context Engineering & Evaluation Science**
>
> A production-grade natural language data analytics agent evaluated against the
> [DataAgentBench (DAB)](https://github.com/ucbepic/DataAgentBench) benchmark.
> Built on principles from the Claude Code architecture leak (March 2026) and
> OpenAI's in-house data agent writeup.

---

## What This Is

Oracle Forge answers complex business questions against heterogeneous enterprise databases.
A user asks: *"Which customer segments had declining repeat purchase rates in Q3, and does that
correlate with support ticket volume?"* The agent navigates two databases, resolves
inconsistently formatted customer IDs, extracts structured facts from free-text fields,
and returns a verifiable answer with an auditable query trace.

### Key Engineering Choices

| Component | Decision | Reason |
|---|---|---|
| **LLM** | Claude claude-opus-4-6 (default) | #3 solo agent on DAB leaderboard (0.4376 pass@1) |
| **Agent core** | DataAgentBench scaffold | Battle-tested multi-DB tool implementations |
| **Context** | Three-layer KB injection | Schema + domain KB + corrections log |
| **Databases** | Docker containers | Reproducible across all team machines |
| **Evaluation** | Sentinel-pattern harness | Trace every call, detect regressions |

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────┐
│                   User Question                       │
└─────────────────────────┬────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────┐
│              OracleAgent (oracle_agent.py)            │
│                                                      │
│  ┌──────────────── Context Manager ────────────────┐  │
│  │ Layer 1: Schema (db_description + hints)        │  │
│  │ Layer 2: Domain KB (join_keys, terminology...)  │  │
│  │ Layer 3: Corrections Log (past failures)        │  │
│  └─────────────────────────────────────────────────┘  │
│                          │                            │
│  ┌──────────────── DataAgent (DAB scaffold) ───────┐  │
│  │  query_db  │  list_db  │  execute_python        │  │
│  │  return_answer                                   │  │
│  └──────┬──────────┬────────────┬──────────────────┘  │
│         │          │            │                      │
└─────────┼──────────┼────────────┼──────────────────────┘
          │          │            │
┌─────────▼──┐ ┌─────▼───┐ ┌─────▼──────────┐
│ PostgreSQL │ │ MongoDB │ │ SQLite / DuckDB │
│ (Docker)   │ │ (Docker) │ │ (DB files)     │
└────────────┘ └─────────┘ └────────────────┘
```

---

## Repository Structure

```
oracle-forge/
├── README.md                   ← This file
├── docker-compose.yml          ← All services (PostgreSQL, MongoDB, agent)
├── .env.example                ← Environment variables template
├── Makefile                    ← Common commands
│
├── agent/                      ← Agent source code
│   ├── Dockerfile
│   ├── AGENT.md                ← Agent context file (loaded at session start)
│   ├── oracle_agent.py         ← Extended DataAgent with 3-layer context
│   ├── context_manager.py      ← Three-layer KB injection system
│   ├── run_benchmark.py        ← Benchmark runner (single query or full run)
│   └── requirements.txt
│
├── DataAgentBench/             ← DAB repository (cloned separately — see setup)
│
├── kb/                         ← LLM Knowledge Base (Karpathy method)
│   ├── README.md               ← KB discipline and injection test protocol
│   ├── architecture/           ← Claude Code memory, OpenAI agent architecture
│   ├── domain/                 ← Join keys, schemas, terminology, unstructured fields
│   ├── evaluation/             ← DAB scoring, submission format
│   └── corrections/            ← Running log of failures → correct approaches
│
├── eval/                       ← Evaluation harness (Sentinel pattern)
│   ├── run_eval.py             ← Full evaluation + regression detection
│   ├── score.py                ← pass@1 scorer against DAB ground truth
│   └── score_log.jsonl         ← Score history (tracks improvement)
│
├── probes/
│   └── probes.md               ← 19 adversarial probes across 4 failure categories
│
├── planning/
│   └── inception_v1.md         ← AI-DLC Inception document with team approval record
│
├── utils/                      ← Shared utility library
│   ├── README.md
│   ├── join_key_resolver.py    ← Auto-detect + resolve cross-DB key mismatches
│   ├── schema_introspection.py ← Programmatic schema discovery (all 4 DB types)
│   ├── multi_pass_retrieval.py ← Multi-pass corrections log search
│   └── tests/                  ← pytest test suite
│
├── signal/                     ← Signal Corps engagement tracking
│   ├── engagement_log.md
│   └── community_log.md
│
└── results/                    ← Benchmark outputs (gitignored except .gitkeep)
    └── .gitkeep
```

---

## Prerequisites

- **Docker Desktop** 24+ (with Docker Compose v2)
- **Git** with LFS (`git lfs install`)
- **Python 3.12+** (for local runs outside Docker)
- **API key**: Anthropic API key or OpenRouter API key
- **DataAgentBench** cloned with datasets (see Step 2 below)

---

## Step-by-Step Setup

### Step 1: Clone This Repository

```bash
git clone https://github.com/YOUR_USERNAME/oracle-forge.git
cd oracle-forge
```

### Step 2: Clone DataAgentBench (with Git LFS for large dataset files)

```bash
# Install Git LFS if not already installed
git lfs install

# Clone DataAgentBench into the oracle-forge directory
git clone https://github.com/ucbepic/DataAgentBench.git DataAgentBench
cd DataAgentBench

# Download the PATENTS database (5GB, stored on Google Drive)
# Option A: Manual — download to DataAgentBench/query_PATENTS/query_dataset/patent_publication.db
# Option B: Script
bash download.sh
cd ..
```

### Step 3: Configure Environment

```bash
# Copy the template
cp .env.example .env

# Edit .env with your API key
# Minimum required: one of ANTHROPIC_API_KEY or OPENROUTER_API_KEY
nano .env   # or use your editor of choice
```

Your `.env` must contain at minimum:
```ini
ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
# OR
OPENROUTER_API_KEY=sk-or-YOUR_KEY_HERE
```

### Step 4: Install Python Dependencies (for local runs)

```bash
# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate      # Linux/Mac
# .venv\Scripts\activate       # Windows

# Install dependencies
pip install -r agent/requirements.txt

# Install DataAgentBench dependencies
cd DataAgentBench && pip install -r requirements.txt && cd ..
```

### Step 5: Build Docker Images

```bash
# Build the Python sandbox image (required by execute_python tool)
docker build -t python-data:3.12 ./DataAgentBench

# Build the Oracle Forge agent image
docker compose build
```

### Step 6: Start Databases

```bash
# Start PostgreSQL and MongoDB in the background
docker compose up -d postgres mongodb

# Verify both are healthy (wait ~30 seconds)
docker compose ps
```

Expected output:
```
NAME                       STATUS          PORTS
oracle-forge-postgres      running (healthy)   0.0.0.0:5432->5432/tcp
oracle-forge-mongodb       running (healthy)   0.0.0.0:27017->27017/tcp
```

### Step 7: Load DAB Datasets

Each DAB dataset has its own loading script. Load in this order (PostgreSQL first):

```bash
# --- PostgreSQL datasets ---
# BookReview
cd DataAgentBench/query_bookreview/query_dataset
psql -h localhost -U postgres -c "CREATE DATABASE books_pg;" 2>/dev/null || true
psql -h localhost -U postgres -d books_pg -f books.sql

# GoogleLocal
cd ../query_googlelocal/query_dataset
psql -h localhost -U postgres -c "CREATE DATABASE googlelocal_pg;" 2>/dev/null || true
psql -h localhost -U postgres -d googlelocal_pg -f googlelocal.sql

# CRMarenaPro
cd ../query_crmarenapro/query_dataset
psql -h localhost -U postgres -c "CREATE DATABASE crm_pg;" 2>/dev/null || true
psql -h localhost -U postgres -d crm_pg -f crm.sql

# Return to project root
cd ../../..

# --- MongoDB datasets ---
# Yelp (mongorestore from dump directory)
mongorestore --uri="mongodb://oracle:oracleforge@localhost:27017/" \
  DataAgentBench/query_yelp/query_dataset/dump/

# Agnews
mongorestore --uri="mongodb://oracle:oracleforge@localhost:27017/" \
  DataAgentBench/query_agnews/query_dataset/dump/
```

> **Note**: SQLite and DuckDB datasets are file-based — no loading step needed. The agent
> reads them directly from the `DataAgentBench/query_*/query_dataset/` directories.

### Step 8: Verify Setup

```bash
# Run a single test query (Yelp dataset, query 1)
docker compose run --rm agent python run_benchmark.py \
  --dataset yelp --query_id 1 --llm claude-opus-4-6

# Expected: a non-empty answer printed to stdout within 5 minutes
# Example: "The average star rating for Yelp businesses in Las Vegas is 3.72"
```

---

## Running the Benchmark

### Single Query

```bash
# Docker (recommended)
docker compose run --rm agent python run_benchmark.py \
  --dataset yelp --query_id 1 --llm claude-opus-4-6

# Local (outside Docker)
cd agent
python run_benchmark.py --dataset yelp --query_id 1 --llm claude-opus-4-6
```

### Specific Datasets (3 trials)

```bash
docker compose run --rm agent python run_benchmark.py \
  --datasets yelp bookreview googlelocal \
  --trials 3 \
  --llm claude-opus-4-6
```

### Full Benchmark (all 12 datasets, 5 trials each = up to 270 runs)

```bash
# This takes several hours — use tmux or screen
docker compose run --rm agent python run_benchmark.py \
  --all --trials 5 --llm claude-opus-4-6

# The runner saves results incrementally — safe to interrupt and resume
```

### Using Make

```bash
make run-yelp                        # Quick test: yelp q1
make benchmark                       # Full benchmark (5 trials)
make benchmark-fast                  # 3 datasets, 3 trials (faster)
make DATASET=bookreview QUERY_ID=2 run-single
```

---

## Evaluation

### Score Latest Results

```bash
python eval/score.py --results results/benchmark_results.json

# Output:
# Overall pass@1: 0.XXXX  (X/54 queries)
# By dataset:
#   yelp               : 0.XXXX
#   bookreview         : 0.XXXX
#   ...
```

### Full Evaluation Report (with regression detection)

```bash
python eval/run_eval.py --results results/benchmark_results.json

# Output:
# Overall pass@1: 0.XXXX
# Failure breakdown:
#   multi_db_routing: X
#   ill_formatted_join: X
#   unstructured_extraction: X
#   domain_knowledge: X
# Regression check: ✅ No regression (improved by +0.XXX)
```

### Score Log (tracks improvement over time)

```bash
cat eval/score_log.jsonl
# Each line is one evaluation run:
# {"timestamp": "...", "overall_pass_at_1": 0.XX, "by_dataset": {...}}
```

---

## Architecture Deep Dive

### Three-Layer Context System

The `agent/context_manager.py` injects three layers of context into every agent run:

**Layer 1 — Schema** (from DataAgentBench `db_description.txt`):
```
Database: yelp_db (DuckDB)
Tables: business (business_id, name, city, state, stars, review_count, is_open)
        tip (business_id, user_id, date, text, compliment_count)
        checkin (business_id, date)
Database: yelp_mongo (MongoDB)
Collections: reviews (business_id, user_id, stars, date, text, useful, funny, cool)
             users (user_id, name, review_count, yelping_since, fans, average_stars)
```

**Layer 2 — Domain KB** (`kb/domain/`):
```
Join Key Glossary:
  yelp: business_id is 22-char alphanumeric, matches directly across DuckDB and MongoDB
  crmarenapro: customer_id (PostgreSQL int) = CUST-{padded} (DuckDB) = C{id} (SQLite)

Domain Terminology:
  Active customer: purchased within last 90 days (check last_purchase_date)
  Revenue: sum(amount) WHERE status NOT IN ('refunded', 'cancelled')
```

**Layer 3 — Corrections Log** (`kb/corrections/corrections_log.md`):
```
KNOWN CORRECTIONS:
  crmarenapro/q3: Direct join on customer_id produces 0 rows due to CUST- prefix.
  Correct: strip prefix → pandas merge
  yelp/q5: SQL LIKE '%wait%' overcounts. Correct: regex in execute_python
```

### Self-Correction Loop

```python
# From oracle_agent.py
while attempt <= max_retries:
    result = DataAgent.run()
    if result.success:
        break
    # Inject correction hint into next attempt's context
    context += f"[HINT: attempt {attempt} failed: {error}. Check join key formats.]"
    attempt += 1
# Log failure to corrections_log.md for future runs
```

---

## Knowledge Base Maintenance

### Adding a New Document

```bash
# 1. Create the document in the appropriate subdirectory
nano kb/domain/my_new_doc.md

# 2. Run the injection test
# Start a fresh Claude session with ONLY your document as context
# Ask a question it should answer
# If correct → document passes; if wrong → revise before committing

# 3. Update the CHANGELOG
echo "## vN — $(date +%Y-%m-%d)\n- Added my_new_doc.md: [description]" >> kb/domain/CHANGELOG.md

# 4. Commit
git add kb/domain/my_new_doc.md kb/domain/CHANGELOG.md
git commit -m "kb(domain): add my_new_doc with injection test passing"
```

### KB Quality Rules (Karpathy Method)

1. **Maximum 400 words per document** — precision over volume.
2. **Every document must pass injection test** before merging.
3. **Remove before adding** — update existing docs instead of adding new ones when possible.
4. **Corrections log is append-only** — never edit past entries, only add new ones.

---

## DAB Leaderboard Submission

```bash
# 1. Run full benchmark (all datasets, 5 trials minimum)
docker compose run --rm agent python run_benchmark.py --all --trials 5

# 2. Build submission JSON
# (run_benchmark.py does this automatically at the end)
ls results/submission.json

# 3. Fork DataAgentBench on GitHub
# https://github.com/ucbepic/DataAgentBench/fork

# 4. Copy submission file and create AGENT.md
cp results/submission.json /path/to/forked-dab/submission/team_oracle_forge_results.json

# 5. Create AGENT.md (required for PR)
cat > /path/to/forked-dab/AGENT.md << EOF
# Oracle Forge Agent

- **Model**: claude-opus-4-6
- **Context**: Three-layer KB (schema + domain + corrections)
- **Self-correction**: Up to 2 retries with diagnostic hints
- **Tool use**: query_db, list_db, execute_python, return_answer
- **Hints**: db_description_withhint.txt enabled
EOF

# 6. Push and open PR
# Title: "Oracle Forge — TRP1 FDE Programme, April 2026"
# Include: pass@1 score, trial count, brief architecture description
```

---

## Running Tests

```bash
# All utility tests
python -m pytest utils/tests/ -v

# Specific module
python -m pytest utils/tests/test_join_key_resolver.py -v

# Expected output:
# PASSED utils/tests/test_join_key_resolver.py::test_detect_cust_prefix
# PASSED utils/tests/test_join_key_resolver.py::test_resolve_join_cust_prefix_to_integer
# ...
# 20 passed in 0.XXs
```

---

## Troubleshooting

### Agent returns empty answer

1. Check `results/traces/` for the JSON trace file.
2. Look at `terminate_reason` — common values:
   - `max_iterations`: agent hit the LLM call limit. Increase `--max_iterations`.
   - `llm_response_failed`: API error. Check your API key and rate limits.
   - `return_answer`: success (check if the answer is actually empty vs. the query has no data).

### PostgreSQL connection refused

```bash
# Check if postgres container is running
docker compose ps postgres
# If not healthy, check logs
docker compose logs postgres
# Restart
docker compose restart postgres
```

### MongoDB authentication error

```bash
# Verify credentials in .env match docker-compose.yml
# Default: oracle / oracleforge
docker compose exec mongodb mongosh --username oracle --password oracleforge
```

### DuckDB / SQLite file not found

```bash
# DAB dataset files must be present in DataAgentBench/query_*/query_dataset/
ls DataAgentBench/query_yelp/query_dataset/
# Should show: yelp.duckdb, db_config.yaml, db_description.txt, query1/, ...
```

### LLM API errors (rate limits)

```bash
# Switch to a cheaper/faster model for testing
docker compose run --rm agent python run_benchmark.py \
  --dataset yelp --query_id 1 --llm claude-sonnet-4-6
```

---

## References

| Resource | URL |
|---|---|
| DataAgentBench repository | https://github.com/ucbepic/DataAgentBench |
| DataAgentBench paper | https://arxiv.org/html/2603.20576 |
| DAB leaderboard | https://ucbepic.github.io/DataAgentBench/ |
| Claude Code architecture analyses | https://github.com/sanbuphy/claude-code-source-code |
| OpenAI data agent writeup | https://openai.com/index/inside-our-in-house-data-agent |
| Karpathy LLM Knowledge Bases | https://academy.dair.ai/blog/llm-knowledge-bases-karpathy |
| AWS AI-DLC framework | https://aws.amazon.com/blogs/devops/ai-driven-development-life-cycle/ |
| Google MCP Toolbox | https://github.com/googleapis/genai-toolbox |
| Cloudflare Workers | https://workers.cloudflare.com |

---

## Team

| Role | Members | Primary deliverables |
|---|---|---|
| Drivers | 2 members | Running agent, evaluation harness, benchmark submission |
| Intelligence Officers | 2 members | Knowledge Base, utility library, adversarial probes |
| Signal Corps | 2 members | External engagement, articles, community log |

---

*TRP1 FDE Programme · Tenacious Intelligence Corp · April 2026*
