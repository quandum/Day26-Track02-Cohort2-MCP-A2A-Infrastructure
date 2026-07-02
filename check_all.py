"""Kiểm tra tổng hợp toàn bộ hệ thống — Lab Ngày 26.

Chạy file này để xác minh tất cả thành phần hoạt động:
  - A2A servers
  - MCP tools (stdio + SSE)
  - Governance + Audit
  - Semantic Router
  - Free Tier Manager
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

results = {"pass": 0, "fail": 0, "warn": 0}

def check(name: str, condition: bool, detail: str = ""):
    if condition:
        results["pass"] += 1
        print(f"  ✅ {name}" + (f" — {detail}" if detail else ""))
    else:
        results["fail"] += 1
        print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))

def warn(name: str, detail: str = ""):
    results["warn"] += 1
    print(f"  ⚠️  {name}" + (f" — {detail}" if detail else ""))


print("=" * 65)
print("  KIỂM TRA TỔNG HỢP — Lab Ngày 26")
print("  Học viên: Trần Mạnh Chánh Quân (2A202600786)")
print("=" * 65)

# ── 1. Môi trường ─────────────────────────────────────────────────────
print("\n📦 1. Môi trường")
try:
    import google.adk; check("google-adk", True, google.adk.__version__ if hasattr(google.adk, '__version__') else "installed")
except: check("google-adk", False, "NOT FOUND")
try:
    import mcp; check("mcp SDK", True)
except: check("mcp SDK", False, "NOT FOUND")
try:
    import httpx; check("httpx", True)
except: check("httpx", False)
try:
    import uvicorn; check("uvicorn", True)
except: check("uvicorn", False)

from lab_utils.env_setup import load_lab_env
load_lab_env()
import os
check("GOOGLE_API_KEY", bool(os.getenv("GOOGLE_API_KEY")), "đã set" if os.getenv("GOOGLE_API_KEY") else "THIẾU")

# ── 2. Free Tier Manager ──────────────────────────────────────────────
print("\n📊 2. Free Tier Manager")
from lab_utils.free_llm_man import get_tier_manager, print_tier_status
tier = get_tier_manager()
st = tier.status()
check("free_llm_man import", True)
check("RPM tracking", st["rpm_limit"] == 10, f"limit={st['rpm_limit']}")
check("RPD tracking", st["rpd_limit"] == 1000, f"limit={st['rpd_limit']}")
check("State file", Path("logs/free_tier_usage.json").exists())
print_tier_status()

# ── 3. A2A Servers ────────────────────────────────────────────────────
print("\n🔗 3. A2A Servers")
import httpx
cards = {
    "search_agent (:8001)": "http://localhost:8001/.well-known/agent-card.json",
    "database_agent (:8002)": "http://localhost:8002/.well-known/agent-card.json",
    "synthesis_agent (:8003)": "http://localhost:8003/.well-known/agent-card.json",
}
all_a2a_ok = True
for name, url in cards.items():
    try:
        r = httpx.get(url, timeout=3)
        ok = r.status_code == 200
        check(name, ok, f"HTTP {r.status_code}")
        all_a2a_ok = all_a2a_ok and ok
    except Exception as e:
        check(name, False, str(e)[:60])
        all_a2a_ok = False

# ── 4. MCP Tools ──────────────────────────────────────────────────────
print("\n🔧 4. MCP Tools (stdio)")
sys.path.insert(0, str(PROJECT_ROOT / "mcp_server"))
from research_tools_server import _search_documents, _sql_query, _summarize_text, _count_words

docs = _search_documents("MCP")
check("search_documents", len(docs) >= 2, f"{len(docs)} results")

rows = _sql_query("SELECT * FROM agent_metrics")
check("sql_query", len(rows) == 3, f"{len(rows)} rows")

bullets = _summarize_text("MCP build. A2A connect.", max_bullets=2)
check("summarize_text", len(bullets) == 2, f"{len(bullets)} bullets")

stats = _count_words("MCP chuẩn hóa giao diện tool")
check("count_words", stats["word_count"] > 0, f"word_count={stats['word_count']}")

# ── 5. MCP SSE Server ─────────────────────────────────────────────────
print("\n🌐 5. MCP SSE Server (:8080)")
from research_tools_server_sse import DOCUMENTS, SQL_ROWS
check("SSE module import", True)
check("SSE documents", len(DOCUMENTS) == 3, f"{len(DOCUMENTS)} docs")
check("SSE sql_rows", len(SQL_ROWS) == 3, f"{len(SQL_ROWS)} rows")

# ── 6. Governance ─────────────────────────────────────────────────────
print("\n🛡️  6. Governance")
from lab_utils.governance import get_guard, AuditLogger
guard = get_guard()
audit = AuditLogger()

conn = guard.authorize_mcp_connection("orchestrator")
check("MCP connection", conn.allowed)
allowed_tools = guard.get_allowed_mcp_tools("orchestrator")
check("MCP tools allowed", len(allowed_tools) == 4,
      f"{len(allowed_tools)} tools: {allowed_tools}")

# SQL guard
bad = guard.authorize_mcp_tool("orchestrator", "sql_query", {"sql": "DROP TABLE x"})
check("SQL DROP blocked", bad.blocked, bad.reason[:50])

good = guard.authorize_mcp_tool("orchestrator", "sql_query", {"sql": "SELECT * FROM agent_metrics"})
check("SQL SELECT allowed", good.allowed)

# A2A dispatch
dispatch = guard.authorize_a2a_dispatch("orchestrator", "search_agent", trace_id="t1")
check("A2A search dispatch", dispatch.allowed)

no_trace = guard.authorize_a2a_dispatch("orchestrator", "database_agent")
check("A2A no-trace HITL", no_trace.needs_approval, "HITL required")

# PII detection
pii = guard.authorize_mcp_tool("orchestrator", "sql_query",
    {"sql": "SELECT * FROM agent_metrics WHERE email = 'test@vinuni.edu.vn'"})
check("PII detection", pii.needs_approval, "HITL required")

# Keyword blocking (Bài tập 5.2)
pw = guard.authorize_mcp_tool("orchestrator", "search_documents", {"query": "tìm password"})
check("Password blocked", pw.blocked, pw.reason[:50])

api_key = guard.authorize_mcp_tool("orchestrator", "search_documents", {"query": "lấy api_key"})
check("api_key blocked", api_key.blocked, api_key.reason[:50])

normal = guard.authorize_mcp_tool("orchestrator", "search_documents", {"query": "MCP protocol"})
check("Normal search allowed", normal.allowed)

# Audit log
summ = audit.summary()
check("Audit log exists", summ.get("allow", 0) > 0,
      f"allow={summ.get('allow',0)} deny={summ.get('deny',0)} hitl={summ.get('hitl_required',0)}")

# ── 7. Semantic Router ────────────────────────────────────────────────
print("\n🧭 7. Semantic Router")
from lab_utils.semantic_router import AgentCapability, SemanticRouter
router = SemanticRouter(agents=[
    AgentCapability("search_agent", "Tìm kiếm web", ["search", "web"]),
    AgentCapability("database_agent", "SQL metrics", ["sql", "database"]),
    AgentCapability("synthesis_agent", "Tổng hợp báo cáo", ["summary", "report"]),
])
candidates = router.route("Tìm tài liệu về MCP", top_k=1)
check("Router hoạt động", len(candidates) > 0, f"top: {candidates[0][0]} ({candidates[0][1]:.3f})")

chain_result = router.route_with_chain("SQL SELECT metrics", ["search_agent", "database_agent", "orchestrator"])
check("route_with_chain", chain_result in ["search_agent", "database_agent", "orchestrator"],
      f"→ {chain_result}")

# ── 8. Agent Registry ─────────────────────────────────────────────────
print("\n📋 8. Agent Registry")
from lab_utils.agent_registry import AgentRegistry, RegisteredAgent
reg = AgentRegistry()
reg.register(RegisteredAgent("search_agent", "http://localhost:8001", "Tìm kiếm"))
reg.register(RegisteredAgent("database_agent", "http://localhost:8002", "SQL"))
check("Registry count", len(reg.list_agents()) == 2)
check("Find by capability", len(reg.find_by_capability("sql")) == 1)

# ── 9. File structure ─────────────────────────────────────────────────
print("\n📁 9. Cấu trúc dự án")
key_files = [
    "agents/orchestrator/agent.py",
    "agents/search_agent/agent.py",
    "agents/database_agent/agent.py",
    "agents/synthesis_agent/agent.py",
    "mcp_server/research_tools_server.py",
    "mcp_server/research_tools_server_sse.py",
    "lab_utils/free_llm_man.py",
    "lab_utils/semantic_router.py",
    "lab_utils/routing_tool.py",
    "lab_utils/agent_registry.py",
    "lab_utils/governance/guard.py",
    "lab_utils/governance/audit.py",
    "lab_utils/governance/adk_callbacks.py",
    "lab_utils/governance/policy.json",
    "lab_utils/governance/rate_limit.py",
    "lab_utils/full_flow.py",
    "logs/governance_audit.jsonl",
    "logs/free_tier_usage.json",
    "work_plan.md",
    "report.md",
    "scripts/start_a2a_servers.sh",
    "scripts/start_capstone.sh",
    "scripts/start_mcp_sse.sh",
    "scripts/stop_a2a_servers.sh",
]
for f in key_files:
    exists = (PROJECT_ROOT / f).exists()
    check(f, exists)

# ── TỔNG KẾT ──────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("  TỔNG KẾT")
print(f"  ✅ Pass: {results['pass']}  ❌ Fail: {results['fail']}  ⚠️  Warn: {results['warn']}")
print("=" * 65)

if results["fail"] == 0:
    print("\n✓ Tất cả kiểm tra đều PASS — hệ thống sẵn sàng!")
else:
    print(f"\n⚠ Có {results['fail']} lỗi cần khắc phục.")

if not all_a2a_ok:
    print("  → A2A servers cần khởi động: bash scripts/start_a2a_servers.sh")
