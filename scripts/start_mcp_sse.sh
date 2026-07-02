#!/usr/bin/env bash
# Khởi động MCP server với transport SSE (HTTP) cổng 8080
# Extension capstone: Transport SSE
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# shellcheck source=_lab_env.sh
source "$ROOT/scripts/_lab_env.sh"
setup_lab_env "$ROOT"

export GOVERNANCE_ACTOR_ID="${GOVERNANCE_ACTOR_ID:-orchestrator}"
export GOVERNANCE_TASK_ID="${GOVERNANCE_TASK_ID:-mcp-sse-session}"

echo "→ Khởi động MCP SSE Server :8080 ..."
echo "  Endpoint: http://localhost:8080/sse"
echo "  Tools: search_documents, sql_query, summarize_text, count_words"

exec "$LAB_PYTHON" mcp_server/research_tools_server_sse.py
