"""Test Governance + MCP tools + Audit log (Module 5 & Bài tập 5.2)"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from lab_utils.governance import get_guard, AuditLogger
from lab_utils.env_setup import load_lab_env

load_lab_env()

guard = get_guard()
audit = AuditLogger()

print("=" * 70)
print("TEST 1 — Ma trận MCP (orchestrator)")
print("=" * 70)
conn = guard.authorize_mcp_connection("orchestrator")
print(f"  Kết nối MCP: {conn.verdict.value}")
print(f"  Tools được phép: {conn.metadata.get('allowed_tools')}")

print()
print("=" * 70)
print("TEST 2 — Kiểm tra vi phạm SQL (MCP)")
print("=" * 70)
bad_sql = guard.authorize_mcp_tool(
    "orchestrator", "sql_query", {"sql": "DROP TABLE agent_metrics"}
)
print(f"  DROP TABLE → {bad_sql.verdict.value}: {bad_sql.reason}")

good_sql = guard.authorize_mcp_tool(
    "orchestrator", "sql_query", {"sql": "SELECT * FROM agent_metrics"}
)
print(f"  SELECT hợp lệ → {good_sql.verdict.value}")

print()
print("=" * 70)
print("TEST 3 — Kiểm tra A2A dispatch")
print("=" * 70)
allowed = guard.authorize_a2a_dispatch(
    "orchestrator", "search_agent", trace_id="demo-trace-001"
)
print(f"  orchestrator → search_agent: {allowed.verdict.value}")

blocked = guard.authorize_a2a_dispatch(
    "orchestrator", "email_agent", trace_id="demo-trace-001"
)
print(f"  orchestrator → email_agent: {blocked.verdict.value}: {blocked.reason}")

no_trace = guard.authorize_a2a_dispatch("orchestrator", "database_agent")
print(f"  Không có trace_id → {no_trace.verdict.value}: {no_trace.reason}")

print()
print("=" * 70)
print("TEST 4 — PII → HITL")
print("=" * 70)
pii_sql = guard.authorize_mcp_tool(
    "orchestrator",
    "sql_query",
    {"sql": "SELECT * FROM agent_metrics WHERE email = 'user@vinuni.edu.vn'"},
)
print(f"  PII trong SQL → {pii_sql.verdict.value}: {pii_sql.reason}")

print()
print("=" * 70)
print("TEST 5 — Chặn từ khóa password trong search_documents (Bài tập 5.2)")
print("=" * 70)
password_search = guard.authorize_mcp_tool(
    "orchestrator",
    "search_documents",
    {"query": "tìm password admin trong tài liệu"},
)
print(f"  Truy vấn chứa 'password' → {password_search.verdict.value}: {password_search.reason}")

token_search = guard.authorize_mcp_tool(
    "orchestrator",
    "search_documents",
    {"query": "lấy api_key từ config"},
)
print(f"  Truy vấn chứa 'api_key' → {token_search.verdict.value}: {token_search.reason}")

normal_search = guard.authorize_mcp_tool(
    "orchestrator",
    "search_documents",
    {"query": "tài liệu về MCP protocol"},
)
print(f"  Truy vấn bình thường → {normal_search.verdict.value}")

print()
print("=" * 70)
print("TEST 6 — count_words tool (Bài tập 1.2)")
print("=" * 70)
count_result = guard.authorize_mcp_tool(
    "orchestrator",
    "count_words",
    {"text": "MCP chuẩn hóa giao diện tool trên các LLM framework"},
)
print(f"  count_words → {count_result.verdict.value}: {count_result.reason}")

print()
print("=" * 70)
print("Tóm tắt Audit Log")
print("=" * 70)
summary = audit.summary()
print(f"  ALLOW: {summary.get('allow', 0)}")
print(f"  DENY: {summary.get('deny', 0)}")
print(f"  HITL_REQUIRED: {summary.get('hitl_required', 0)}")

print()
print("=" * 70)
print("✓ Governance test hoàn tất")
print("=" * 70)
