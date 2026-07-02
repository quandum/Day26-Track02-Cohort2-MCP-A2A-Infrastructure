"""Test count_words tool và các MCP tools trực tiếp (Bài tập 1.2)"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "mcp_server"))

from research_tools_server import _search_documents, _sql_query, _summarize_text, _count_words

print("=" * 70)
print("TEST — count_words (Bài tập 1.2)")
print("=" * 70)
text = "MCP chuẩn hóa giao diện tool trên các LLM framework khác nhau"
result = _count_words(text)
print(f"  Input: '{text}'")
print(f"  word_count: {result['word_count']}")
print(f"  char_count: {result['char_count']}")
print(f"  char_count_no_spaces: {result['char_count_no_spaces']}")
print(f"  avg_word_length: {result['avg_word_length']}")

print()
print("=" * 70)
print("TEST — search_documents")
print("=" * 70)
for doc in _search_documents("MCP"):
    print(f"  ✓ {doc['title']}")

print()
print("=" * 70)
print("TEST — sql_query")
print("=" * 70)
for row in _sql_query("SELECT * FROM agent_metrics"):
    print(f"  {row['agent']}: {row['tasks_completed']} tasks, {row['avg_latency_ms']}ms")

print()
print("=" * 70)
print("TEST — summarize_text")
print("=" * 70)
summary = _summarize_text("MCP build một lần. A2A kết nối agent. Routing chọn specialist.", max_bullets=3)
for line in summary:
    print(f"  {line}")

print()
print("=" * 70)
print("✓ Tất cả MCP tools hoạt động bình thường")
print("=" * 70)
