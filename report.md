# Báo cáo thực hành — Lab Ngày 26: Hạ Tầng MCP/A2A & Agentic Routing

**Học viên:** Trần Mạnh Chánh Quân  
**Mã học viên:** 2A202600786  
**Khóa học:** AICB-P2T2 · Tuần 6 · Chương 6  
**Framework:** Google Agent Development Kit (ADK)  
**Ngày thực hiện:** 02/07/2026  
**Môi trường:** Python 3.12 (pip, không dùng Conda riêng)

---

## 1. Tóm tắt

Lab này xây dựng hệ thống **4 agent** (1 orchestrator + 3 specialist: search, database, synthesis) giao tiếp qua **MCP** (Model Context Protocol) và **A2A** (Agent-to-Agent). Hệ thống tích hợp **semantic routing**, **data governance** đa lớp và **audit trace** tự động.

---

## 2. Kiến trúc triển khai

```
Orchestrator (:8000 ADK Web)
  ├── A2A → search_agent     (:8001) — search_web
  ├── A2A → database_agent   (:8002) — run_sql_query (chỉ SELECT)
  ├── A2A → synthesis_agent  (:8003) — synthesize_report
  └── MCP → research_tools   (stdio) — search_documents, sql_query, summarize_text, count_words
```

**Governance layer:** `GovernanceGuard` → `policy.json` → `AuditLogger` → `logs/governance_audit.jsonl`

---

## 3. Kết quả từng Module

### Module 0 — Thiết lập môi trường

| Tiêu chí | Kết quả |
|----------|---------|
| Python + pip packages | ĐÃ CÀI (google-adk, mcp, uvicorn, httpx, ...) |
| `GOOGLE_API_KEY` trong `.env` | ✅ ĐÃ CẤU HÌNH |
| `PYTHONPATH=$PWD` | ✅ ĐÃ SET |
| A2A servers (:8001-:8003) | ✅ ĐANG CHẠY |

### Module 1 — MCP Server

| Yêu cầu | Kết quả |
|----------|---------|
| 3 tool MCP (search_documents, sql_query, summarize_text) | ✅ HOẠT ĐỘNG |
| Tool thứ 4 `count_words` | ✅ ĐÃ THÊM (Bài tập 1.2) |
| Governance enforcement | ✅ HOẠT ĐỘNG (block DROP, allow SELECT) |
| Transport stdio | ✅ HOẠT ĐỘNG |

**📝 Bài tập 1.1 — Trả lời:**

| # | Câu hỏi | Trả lời |
|---|---------|--------|
| 1 | Ba tool expose? | `search_documents`, `sql_query`, `summarize_text` |
| 2 | Governance SQL? | `_sql_query` kiểm tra `AGENT_METRICS` trong SQL; từ chối DDL/DML |
| 3 | Vì sao stdio? | Đơn giản cho dev local, không cần mở cổng, dễ debug |

**📝 Bài tập 1.2 — Thêm tool `count_words`:** ✅ ĐÃ HOÀN THÀNH
- File: `mcp_server/research_tools_server.py`
- Tool `count_words` đếm: `word_count`, `char_count`, `char_count_no_spaces`, `avg_word_length`
- Đã thêm vào `list_tools()`, `call_tool()`, `lab_utils/governance/policy.json`

### Module 2 — A2A Protocol

| Yêu cầu | Kết quả |
|----------|---------|
| search_agent :8001 | ✅ HOẠT ĐỘNG |
| database_agent :8002 | ✅ HOẠT ĐỘNG |
| synthesis_agent :8003 | ✅ HOẠT ĐỘNG |
| Orchestrator → RemoteA2aAgent | ✅ KẾT NỐI THÀNH CÔNG |

**📝 Bài tập 2.1 — So sánh A2A vs Local:**

| Tiêu chí | A2A (Remote) | Sub-Agent Local |
|----------|-------------|------------------|
| Triển khai | Process riêng, HTTP | Cùng process |
| Hiệu năng | Network overhead | Gọi hàm trực tiếp |
| Cô lập state | Hoàn toàn | Có thể chia sẻ |
| Phù hợp khi | Microservices, scale | Prototype, monolith |

### Module 3 — Agentic Routing

| Yêu cầu | Kết quả |
|----------|---------|
| Semantic router | ✅ HOẠT ĐỘNG (bag-of-words + cosine similarity) |
| Agent registry | ✅ HOẠT ĐỘNG (in-memory) |
| `suggest_routing` tool | ✅ HOẠT ĐỘNG |
| `route_with_chain` fallback | ✅ HOẠT ĐỘNG (Bài tập 3.1) |

**📝 Bài tập 3.1 — Fallback Chain:** ✅ ĐÃ HOÀN THÀNH
- File: `lab_utils/semantic_router.py`
- Phương thức `route_with_chain(request, chain)` thử route chính trước; nếu score < threshold thì duyệt fallback chain có thứ tự

### Module 4 — Capstone ADK Web

| Yêu cầu | Kết quả |
|----------|---------|
| A2A servers :8001-:8003 | ✅ ĐANG CHẠY |
| ADK Web :8000 | ⚠️ Cần nạp credit Gemini API |
| Full flow A2A (W1) | ⚠️ Chờ credit API (429 RESOURCE_EXHAUSTED) |
| Full flow MCP (W2) | ⚠️ Chờ credit API |

> **Ghi chú:** API Gemini trả về 429 RESOURCE_EXHAUSTED do hết prepayment credits. Cần nạp credit tại https://ai.studio/projects. Toàn bộ code và infrastructure đã sẵn sàng.

**📝 Kết quả 5 prompt ADK Web:** (sẽ điền sau khi nạp credit API)

### Module 5 — Governance & Observability

| Yêu cầu | Kết quả |
|----------|---------|
| Capability matrix | ✅ HOẠT ĐỘNG (4 MCP tools cho orchestrator) |
| SQL guard (chỉ SELECT) | ✅ HOẠT ĐỘNG (DROP TABLE → DENY) |
| Rate limit (30/phút) | ✅ HOẠT ĐỘNG |
| HITL (PII, thiếu trace_id) | ✅ HOẠT ĐỘNG (email→HITL; no trace_id→HITL) |
| Audit log | ✅ 10 bản ghi: 4 ALLOW, 4 DENY, 2 HITL |
| Keyword blocking (password) | ✅ HOẠT ĐỘNG (Bài tập 5.2) |
| Runaway prevention (50 calls) | ✅ HOẠT ĐỘNG |

**📝 Bài tập 5.1 — Ma trận capability:**

| Agent | Được phép | Bị chặn | HITL trigger |
|-------|-----------|--------|--------------|
| orchestrator | MCP tools, A2A dispatch | MCP từ agent khác | PII, thiếu trace_id |
| search_agent | search_web | write, delete, send_email | — |
| database_agent | SELECT | DDL, DML, TRUNCATE | PII |
| synthesis_agent | synthesize_report | Thu thập dữ liệu mới | — |

**📝 Bài tập 5.2 — Mở rộng policy:** ✅ ĐÃ HOÀN THÀNH
- File: `lab_utils/governance/guard.py`
- Thêm rule chặn từ khóa nhạy cảm trong `search_documents`: `password`, `token`, `secret`, `api_key`, `private_key`
- `synthesis_agent` đã có sẵn trong `allowed_targets` của orchestrator

---

## 4. Audit Log (kết quả thực tế)

```
Tổng: 10 bản ghi
  ALLOW:         4  (SELECT, A2A dispatch, search_documents, count_words)
  DENY:          4  (DROP TABLE, email_agent, password, api_key)
  HITL_REQUIRED: 2  (PII email trong SQL, thiếu trace_id)
```

File: `logs/governance_audit.jsonl` — ghi tự động mọi lần gọi MCP/A2A

---

## 5. Khó khăn & bài học

| Khó khăn | Giải pháp |
|----------|-----------|
| Google AI Studio hết credit (429) | Nạp credit tại https://ai.studio/projects |
| Không cần Conda riêng | Dùng pip system Python, vẫn hoạt động |

---

## 6. Kết luận

Lab đã hoàn thành các mục tiêu:
1. ✅ Thiết kế và triển khai MCP server với 4 tool (thêm `count_words`)
2. ✅ Triển khai A2A giữa 4 agent bằng ADK (3 servers đang chạy)
3. ✅ Xây dựng semantic routing với fallback chain (`route_with_chain`)
4. ✅ Áp dụng data governance đa lớp (SQL guard, PII, keyword block, rate limit, audit)
5. ⚠️ Full flow + ADK Web: code sẵn sàng, cần nạp credit Gemini API

**Điểm tự đánh giá:** 8/10 (trừ 2 điểm do chưa chạy được full flow vì hết credit API)

---

## Chữ ký xác nhận

**Học viên:** Trần Mạnh Chánh Quân  
**Ngày:** 02/07/2026
