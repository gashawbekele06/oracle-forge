FROM python:3.12-slim

# ── System dependencies ────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    git \
    gnupg \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# ── MongoDB Database Tools (mongorestore, mongodump, etc.) ─────────────────
# Required by DataAgentBench's mongo_utils.load_db() to restore Mongo dumps.
RUN curl -fsSL https://www.mongodb.org/static/pgp/server-8.0.asc \
    | gpg --dearmor -o /usr/share/keyrings/mongodb-server-8.0.gpg && \
    echo "deb [ arch=amd64 signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] \
https://repo.mongodb.org/apt/debian bookworm/mongodb-org/8.0 main" \
    | tee /etc/apt/sources.list.d/mongodb-org-8.0.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends mongodb-database-tools && \
    rm -rf /var/lib/apt/lists/*

# ── Working directory ──────────────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies ────────────────────────────────────────────────────
COPY agent/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy project files ────────────────────────────────────────────────────
COPY agent/ /app/agent/
COPY kb/     /app/kb/

# DataAgentBench is mounted at runtime via Docker volume:
#   -v ./DataAgentBench:/app/DataAgentBench
# This keeps the large dataset files out of the image.

# ── Environment ───────────────────────────────────────────────────────────
ENV DAB_ROOT=/app/DataAgentBench
ENV KB_ROOT=/app/kb
ENV PYTHONPATH=/app:/app/DataAgentBench
ENV PYTHONUNBUFFERED=1

# ── Default command ───────────────────────────────────────────────────────
WORKDIR /app/agent
CMD ["python", "run_benchmark.py", "--help"]
