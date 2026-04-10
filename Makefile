# Oracle Forge — Makefile
# ========================
# Common development and operations commands.
#
# Usage:
#   make setup          # Initial setup
#   make build          # Build Docker images
#   make up             # Start databases
#   make run-yelp       # Quick test: run Yelp q1
#   make benchmark      # Full benchmark (all datasets, 5 trials)
#   make score          # Score the latest results
#   make test           # Run unit tests

.PHONY: setup build up down run-yelp run-single benchmark score test \
        load-postgres load-mongo clean help

# ── Config ────────────────────────────────────────────────────────────
LLM ?= claude-opus-4-6
TRIALS ?= 5
DATASET ?= yelp
QUERY_ID ?= 1

# ── Setup ──────────────────────────────────────────────────────────────
setup:
	@echo "Setting up Oracle Forge..."
	@test -f .env || (cp .env.example .env && echo "Created .env — fill in your API keys!")
	@cd DataAgentBench && pip install -r requirements.txt 2>/dev/null || true
	@pip install -r agent/requirements.txt
	@echo "Setup complete. Edit .env with your API keys."

# ── Docker ────────────────────────────────────────────────────────────
build:
	docker build -t python-data:3.12 ./DataAgentBench
	docker compose build

up:
	docker compose up -d postgres mongodb
	@echo "Waiting for databases to be ready..."
	@sleep 5
	@docker compose ps

down:
	docker compose down

# ── Dataset Loading ────────────────────────────────────────────────────
load-postgres:
	@echo "Loading PostgreSQL datasets into Docker container..."
	docker compose exec postgres bash -c '\
		for sql_file in /dab/query_*/query_dataset/*.sql /dab/query_*/query_dataset/*.dump; do \
			[ -f "$$sql_file" ] && echo "Loading $$sql_file" && \
			psql -U postgres -f "$$sql_file" 2>/dev/null || true; \
		done'

load-mongo:
	@echo "Loading MongoDB datasets into Docker container..."
	docker compose exec mongodb bash -c '\
		for dump_dir in /dab/query_*/query_dataset/dump; do \
			[ -d "$$dump_dir" ] && echo "Restoring $$dump_dir" && \
			mongorestore --uri="$$MONGO_URI" "$$dump_dir" 2>/dev/null || true; \
		done'

# ── Run Agent ─────────────────────────────────────────────────────────
run-yelp:
	docker compose run --rm agent python run_benchmark.py \
		--dataset yelp --query_id 1 --llm $(LLM)

run-single:
	docker compose run --rm agent python run_benchmark.py \
		--dataset $(DATASET) --query_id $(QUERY_ID) --llm $(LLM)

benchmark:
	docker compose run --rm agent python run_benchmark.py \
		--all --trials $(TRIALS) --llm $(LLM)

benchmark-fast:
	docker compose run --rm agent python run_benchmark.py \
		--datasets yelp bookreview googlelocal --trials 3 --llm claude-sonnet-4-6

# ── Evaluation ────────────────────────────────────────────────────────
score:
	python eval/score.py --results results/benchmark_results.json

eval:
	python eval/run_eval.py --results results/benchmark_results.json

# ── Testing ───────────────────────────────────────────────────────────
test:
	cd oracle-forge && python -m pytest utils/tests/ -v

test-context:
	python -c "from agent.context_manager import ContextManager; \
		m = ContextManager(); print(m.get_architecture_context()[:200])"

# ── Git Helpers ───────────────────────────────────────────────────────
submit-pr:
	@echo "Preparing DAB leaderboard submission..."
	@test -f results/submission.json || (echo "Run 'make benchmark' first" && exit 1)
	@echo "Submission JSON ready: results/submission.json"
	@echo "Next: fork ucbepic/DataAgentBench and open a PR"

# ── Cleanup ───────────────────────────────────────────────────────────
clean:
	docker compose down -v
	find results/traces -name "*.json" -delete 2>/dev/null || true

# ── Help ──────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "Oracle Forge — Available Commands"
	@echo "==================================="
	@echo "  make setup           Initial project setup"
	@echo "  make build           Build Docker images"
	@echo "  make up              Start postgres + mongodb"
	@echo "  make load-postgres   Load PostgreSQL DAB datasets"
	@echo "  make load-mongo      Load MongoDB DAB datasets"
	@echo "  make run-yelp        Quick test (yelp q1)"
	@echo "  make run-single      Run single query (DATASET=x QUERY_ID=y)"
	@echo "  make benchmark       Full benchmark (5 trials, all datasets)"
	@echo "  make benchmark-fast  Fast benchmark (3 datasets, 3 trials)"
	@echo "  make score           Score latest results"
	@echo "  make test            Run unit tests"
	@echo "  make clean           Remove containers and trace files"
	@echo ""
	@echo "Environment overrides:"
	@echo "  LLM=claude-sonnet-4-6 make benchmark"
	@echo "  TRIALS=3 make benchmark"
	@echo ""
