"""Synthesis specialist — expose qua A2A cổng 8003 (có governance)."""

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
print("[synthesis_agent] Free Tier status:")
print_tier_status()

from lab_utils.governance import (
    get_guard,
    governance_before_agent_callback,
    governance_before_tool_callback,
)

guard = get_guard()


def synthesize_report(findings: str, audience: str = "technical") -> dict:
    """Tổng hợp phát hiện nghiên cứu thành báo cáo có cấu trúc.

    Args:
        findings: Nội dung thô từ search, database hoặc MCP tools.
        audience: Đối tượng đọc — technical hoặc executive.

    Returns:
        Dict báo cáo với executive_summary và key_points.
    """
    decision = guard.authorize_agent_tool(
        actor_id="synthesis_agent",
        tool_name="synthesize_report",
        arguments={"findings": findings[:500], "audience": audience},
    )
    if not decision.allowed:
        return {"status": "blocked", "reason": decision.reason}

    sentences = [s.strip() for s in findings.replace("\n", " ").split(".") if s.strip()]
    key_points = [s for s in sentences[:5] if len(s) > 10]

    if audience == "executive":
        summary = (
            f"Báo cáo tóm tắt ({len(key_points)} điểm chính): "
            + (key_points[0] if key_points else "Không có dữ liệu đủ để tổng hợp.")
        )
    else:
        summary = "Tổng hợp kỹ thuật từ " + str(len(sentences)) + " câu nguồn."

    return {
        "status": "success",
        "audience": audience,
        "executive_summary": summary,
        "key_points": key_points or ["Không trích xuất được điểm chính."],
        "word_count": len(findings.split()),
    }


root_agent = Agent(
    name="synthesis_agent",
    model="gemini-2.5-flash",
    description="Tổng hợp kết quả nghiên cứu thành báo cáo cuối có cấu trúc.",
    instruction=(
        "Bạn là chuyên gia tổng hợp báo cáo nghiên cứu. "
        "Dùng synthesize_report để biến findings thô thành executive_summary và key_points. "
        "Không thu thập dữ liệu mới — chỉ tổng hợp input đã có."
    ),
    tools=[synthesize_report],
    before_tool_callback=governance_before_tool_callback,
    before_agent_callback=governance_before_agent_callback,
)

a2a_app = to_a2a(root_agent, port=8003)
