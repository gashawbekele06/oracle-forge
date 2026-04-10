#!/usr/bin/env bash
# ============================================================
# apply_patches.sh — Apply Oracle Forge runtime patches to DataAgentBench
#
# Run this ONCE after cloning DataAgentBench:
#   bash patches/apply_patches.sh
#
# What it patches:
#   1. DataAgent.py          — smart LLM routing (OpenAI / OpenRouter / Anthropic)
#   2. LocalExecTool.py      — subprocess-based Python executor (replaces autogen Docker-in-Docker)
#   3. mongo_utils.py        — pass --uri to mongorestore for Docker network routing
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAB_DIR="$(cd "$SCRIPT_DIR/../DataAgentBench" && pwd)"

echo "Applying Oracle Forge patches to DataAgentBench at: $DAB_DIR"

cp "$SCRIPT_DIR/common_scaffold/DataAgent.py" \
   "$DAB_DIR/common_scaffold/DataAgent.py"
echo "  ✓ DataAgent.py (LLM routing)"

cp "$SCRIPT_DIR/common_scaffold/tools/LocalExecTool.py" \
   "$DAB_DIR/common_scaffold/tools/LocalExecTool.py"
echo "  ✓ LocalExecTool.py (subprocess executor)"

cp "$SCRIPT_DIR/common_scaffold/tools/db_utils/mongo_utils.py" \
   "$DAB_DIR/common_scaffold/tools/db_utils/mongo_utils.py"
echo "  ✓ mongo_utils.py (mongorestore --uri fix)"

echo ""
echo "All patches applied successfully!"
