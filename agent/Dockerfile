FROM python:3.12-slim

# ── System dependencies ────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ──────────────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies ────────────────────────────────────────────────────
COPY agent/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ── DataAgentBench sandbox image (for execute_python tool) ─────────────────
# Build the lightweight execution sandbox separately
RUN pip install --no-cache-dir pandas pyarrow

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

# ── Default command: interactive agent shell ──────────────────────────────
WORKDIR /app/agent
CMD ["python", "run_benchmark.py", "--help"]
