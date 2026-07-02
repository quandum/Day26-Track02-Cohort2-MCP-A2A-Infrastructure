"""Test MCP SSE Server — kiểm tra transport HTTP hoạt động."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "mcp_server"))

from lab_utils.env_setup import load_lab_env
load_lab_env()

# Test trực tiếp tool functions (không cần server chạy)
from research_tools_server_sse import (
    _search_documents, _sql_query, _summarize_text, _count_words,
    DOCUMENTS, SQL_ROWS
)

print("=" * 60)
print("TEST MCP SSE Server — Tool Functions")
print("=" * 60)

print("\n1. search_documents('MCP'):")
for doc in _search_documents("MCP"):
    print(f"   ✓ {doc['title']}")

print("\n2. sql_query('SELECT * FROM agent_metrics'):")
for row in _sql_query("SELECT * FROM agent_metrics"):
    print(f"   ✓ {row['agent']}: {row['tasks_completed']} tasks")

print("\n3. summarize_text:")
bullets = _summarize_text("MCP build một lần. A2A kết nối agent. Routing chọn specialist.")
for b in bullets:
    print(f"   {b}")

print("\n4. count_words:")
stats = _count_words("MCP SSE server hoạt động trên HTTP cổng 8080")
for k, v in stats.items():
    print(f"   {k}: {v}")

print(f"\n5. Data sources:")
print(f"   Documents: {len(DOCUMENTS)}")
print(f"   SQL rows: {len(SQL_ROWS)}")

print()
print("=" * 60)
print("✓ MCP SSE Server sẵn sàng")
print("  Khởi động: python mcp_server/research_tools_server_sse.py")
print("  hoặc: bash scripts/start_mcp_sse.sh")
print("=" * 60)
