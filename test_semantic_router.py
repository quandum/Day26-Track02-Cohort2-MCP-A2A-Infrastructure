"""Test Semantic Router + Fallback Chain (Bài tập 3.1)"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from lab_utils.semantic_router import AgentCapability, SemanticRouter

router = SemanticRouter(
    agents=[
        AgentCapability(
            name="search_agent",
            description="Tìm kiếm web tài liệu nghiên cứu bằng chứng",
            tags=["search", "web", "documents"],
        ),
        AgentCapability(
            name="database_agent",
            description="SQL metrics phân tích database truy vấn SELECT",
            tags=["sql", "metrics", "database"],
        ),
        AgentCapability(
            name="synthesis_agent",
            description="Tóm tắt kết hợp kết quả thành báo cáo cuối",
            tags=["summary", "report", "synthesis"],
        ),
    ]
)

print("=" * 70)
print("TEST 1 — Semantic Router cơ bản")
print("=" * 70)
test_queries = [
    "Tìm bài viết về việc áp dụng giao thức MCP",
    "SELECT độ trễ trung bình từ agent_metrics",
    "Viết tóm tắt một trang về kết quả nghiên cứu",
    "Xin chào, bạn làm được gì?",
]
print(f"{'Truy vấn':<50} {'Định tuyến tới':<20} Điểm")
print("-" * 80)
for query in test_queries:
    candidates = router.route(query, top_k=1)
    target = router.route_with_fallback(query, fallback="orchestrator")
    score = candidates[0][1] if candidates else 0.0
    print(f"{query[:48]:<50} {target:<20} {score:.3f}")

print()
print("=" * 70)
print("TEST 2 — Fallback Chain (Bài tập 3.1)")
print("=" * 70)
chain = ["search_agent", "database_agent", "orchestrator"]
test_chain = [
    "Một câu hỏi không liên quan gì đến tìm kiếm hay database cả",
    "Tôi muốn tìm tài liệu về machine learning",
]
for query in test_chain:
    result = router.route_with_chain(query, chain)
    candidates = router.route(query, top_k=1)
    score = candidates[0][1] if candidates else 0.0
    status = "✓ Route chính" if score >= router.threshold else "→ Fallback"
    print(f"  Query: '{query[:60]}...'")
    print(f"    Score: {score:.3f} → {status} → agent: {result}")
    print()

print("=" * 70)
print("✓ Semantic Router + Fallback Chain hoạt động")
print("=" * 70)
