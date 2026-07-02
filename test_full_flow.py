"""Demo Full Flow: Orchestrator → A2A + MCP (Module 4)"""
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from lab_utils.free_llm_man import get_tier_manager, print_tier_status
from lab_utils.full_flow import check_a2a_servers, print_flow_summary, run_full_flow


async def main():
    print("=" * 70)
    print("DEMO FULL FLOW — Orchestrator → A2A + MCP")
    print("=" * 70)

    # Hiển thị trạng thái Free Tier
    tier = get_tier_manager()
    print_tier_status()

    # Kiểm tra A2A servers
    ok, errors = check_a2a_servers()
    if not ok:
        print("✗ A2A servers chưa sẵn sàng:")
        for e in errors:
            print(f"  - {e}")
        return
    print("✓ A2A servers OK\n")

    # Ví dụ 1: A2A search delegation
    print("--- Ví dụ 1: A2A → search_agent ---")
    try:
        result_1 = await run_full_flow(
            "Transfer sang search_agent để tìm kiếm web về multi-agent orchestration.",
            verbose=True,
        )
        print_flow_summary(result_1)
    except Exception as e:
        print(f"⚠ Ví dụ 1 lỗi: {e}")

    print()
    print("--- Ví dụ 2: MCP + suggest_routing ---")
    try:
        result_2 = await run_full_flow(
            "Gọi suggest_routing cho câu: 'SELECT độ trễ trung bình từ agent_metrics'. "
            "Rồi giải thích kết quả.",
            verbose=True,
        )
        print_flow_summary(result_2)
    except Exception as e:
        print(f"⚠ Ví dụ 2 lỗi: {e}")

    print()
    print("=" * 70)
    print("✓ Full flow demo hoàn tất")
    print_tier_status()
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
