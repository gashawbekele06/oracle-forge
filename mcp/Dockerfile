FROM python:3.12-slim

# ── System dependencies ────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ──────────────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies ────────────────────────────────────────────────────
COPY mcp/requirements.txt /app/mcp/requirements.txt
RUN pip install --no-cache-dir -r /app/mcp/requirements.txt

# ── Agent dependencies (for DataAgent / ContextManager imports) ────────────
COPY agent/requirements.txt /app/agent/requirements.txt
RUN pip install --no-cache-dir -r /app/agent/requirements.txt

# ── Copy project files ─────────────────────────────────────────────────────
COPY mcp/    /app/mcp/
COPY agent/  /app/agent/
COPY kb/     /app/kb/

# DataAgentBench and results are mounted at runtime via Docker volumes:
#   -v ./DataAgentBench:/app/DataAgentBench
#   -v ./results:/app/results

# ── Environment ───────────────────────────────────────────────────────────
ENV DAB_ROOT=/app/DataAgentBench
ENV KB_ROOT=/app/kb
ENV PYTHONPATH=/app:/app/DataAgentBench:/app/agent
ENV PYTHONUNBUFFERED=1

# ── Expose SSE port ───────────────────────────────────────────────────────
EXPOSE 8000

# ── Default command: SSE transport for Docker ─────────────────────────────
WORKDIR /app
CMD ["python", "mcp/server.py", "--transport", "sse", "--port", "8000"]
