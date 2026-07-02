"""Database specialist — expose qua A2A cổng 8002 (có governance)."""

import sys
from pathlib import Path

from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lab_utils.env_setup import load_lab_env, require_api_key

load_lab_env()
require_api_key()

from lab_utils.free_llm_man import get_tier_manager, print_tier_status

tier = get_tier_manager()
print("[database_agent] Free Tier status:")
print_tier_status()

from lab_utils.governance import (
    get_guard,
    governance_before_agent_callback,
    governance_before_tool_callback,
)

guard = get_guard()


def run_sql_query(sql: str) -> dict:
    """Thực thi truy vấn SQL chỉ đọc trên metrics agent.

    Args:
        sql: Câu lệnh SELECT.

    Returns:
        Kết quả truy vấn dạng dict.
    """
    decision = guard.authorize_agent_tool(
        actor_id="database_agent",
        tool_name="run_sql_query",
        arguments={"sql": sql},
    )
    if not decision.allowed:
        return {"status": "blocked", "reason": decision.reason}
    if decision.needs_approval:
        return {
            "status": "hitl_required",
            "reason": decision.reason,
            "message": "Cần phê duyệt trước khi chạy truy vấn có dữ liệu nhạy cảm.",
        }

    rows = [
        {"agent": "search_agent", "tasks_completed": 42, "avg_latency_ms": 820},
        {"agent": "database_agent", "tasks_completed": 31, "avg_latency_ms": 1100},
    ]
    return {"status": "success", "rows": rows}


root_agent = Agent(
    name="database_agent",
    model="gemini-2.5-flash",
    description="Truy vấn database chỉ đọc và trả về metrics có cấu trúc.",
    instruction=(
        "Bạn là chuyên gia database. Chỉ chạy truy vấn SELECT qua run_sql_query. "
        "Không bao giờ thử DDL hoặc câu lệnh ghi. "
        "Nếu governance trả về blocked hoặc hitl_required, báo cho caller."
    ),
    tools=[run_sql_query],
    before_tool_callback=governance_before_tool_callback,
    before_agent_callback=governance_before_agent_callback,
)

a2a_app = to_a2a(root_agent, port=8002)
