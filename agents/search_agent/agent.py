"""Search specialist — expose qua A2A cổng 8001 (có governance)."""

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
print("[search_agent] Free Tier status:")
print_tier_status()

from lab_utils.governance import (
    get_guard,
    governance_before_agent_callback,
    governance_before_tool_callback,
)

guard = get_guard()


def search_web(query: str) -> dict:
    """Tìm kiếm web theo chủ đề.

    Args:
        query: Câu truy vấn tìm kiếm.

    Returns:
        Dict chứa kết quả tìm kiếm (mô phỏng cho lớp học).
    """
    decision = guard.authorize_agent_tool(
        actor_id="search_agent",
        tool_name="search_web",
        arguments={"query": query},
    )
    if not decision.allowed:
        return {"status": "blocked", "reason": decision.reason}

    return {
        "status": "success",
        "query": query,
        "results": [
            {
                "title": f"Kết quả cho: {query}",
                "snippet": "MCP chuẩn hóa giao diện tool trên các LLM framework.",
            },
            {
                "title": "Tổng quan giao thức A2A",
                "snippet": "Agent card tại /.well-known/agent-card.json mô tả capability.",
            },
        ],
    }


root_agent = Agent(
    name="search_agent",
    model="gemini-2.5-flash",
    description="Tìm kiếm web và trả về đoạn trích liên quan cho tác vụ nghiên cứu.",
    instruction=(
        "Bạn là chuyên gia tìm kiếm web. Dùng search_web để tìm thông tin. "
        "Luôn trả lời bằng văn bản rõ ràng (tiêu đề nguồn + snippet). "
        "Không được ghi, xóa hoặc gửi email — chỉ đọc và tìm kiếm."
    ),
    tools=[search_web],
    before_tool_callback=governance_before_tool_callback,
    before_agent_callback=governance_before_agent_callback,
)

a2a_app = to_a2a(root_agent, port=8001)
