# Kế hoạch thực hiện — Lab Ngày 26: Hạ Tầng MCP/A2A & Agentic Routing

**Học viên:** Trần Mạnh Chánh Quân  
**Mã học viên:** 2A202600786  
**Khóa học:** AICB-P2T2 · Tuần 6 · Chương 6  
**Framework:** Google Agent Development Kit (ADK)  
**Ngày lập kế hoạch:** 02/07/2026

---

## Mục lục

1. [Tổng quan dự án](#1-tổng-quan-dự-án)
2. [Kiến trúc hệ thống](#2-kiến-trúc-hệ-thống)
3. [Kế hoạch từng bước](#3-kế-hoạch-từng-bước)
4. [Bảng phân công & tiến độ](#4-bảng-phân-công--tiến-độ)
5. [Tiêu chí đánh giá hoàn thành](#5-tiêu-chí-đánh-giá-hoàn-thành)
6. [Rủi ro & giải pháp](#6-rủi-ro--giải-pháp)

---

## 1. Tổng quan dự án

### Mục tiêu

Xây dựng hệ thống **4 agent** (1 orchestrator + 3 specialist) giao tiếp qua **MCP** (Model Context Protocol) và **A2A** (Agent-to-Agent), tích hợp **semantic routing**, **data governance** và **audit trace**.

### Sản phẩm cuối ngày

| Thành phần | Yêu cầu | Trạng thái |
|------------|---------|-----------|
| MCP Server | 3+ tools qua stdio | Cần hoàn thiện |
| Agent Registry | Health check + khám phá capability | Cần hoàn thiện |
| Semantic Router | Định tuyến request → specialist | Cần hoàn thiện |
| Demo Multi-Agent | Orchestrator + 3 specialist qua A2A | Cần hoàn thiện |
| Trace | Toàn bộ luồng trong log | Cần hoàn thiện |
| Data Governance | Policy MCP/A2A + audit log + HITL | Cần hoàn thiện |

---

## 2. Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────┐
│                ORCHESTRATOR (ADK) — Cổng 8000               │
│  suggest_routing → SemanticRouter → A2A dispatch            │
│  MCP Tools (stdio): search_documents, sql_query, summarize  │
└──────┬────────────────────┬──────────────────┬──────────────┘
       │ A2A (HTTP)         │ A2A (HTTP)       │ A2A (HTTP)
       ▼                    ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│ Search Agent │  │Database Agent│  │ Synthesis Agent  │
│   :8001      │  │   :8002     │  │     :8003        │
│ search_web() │  │run_sql_query │  │synthesize_report │
└──────────────┘  └──────────────┘  └──────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  MCP Tools Server   │
              │  (stdio subprocess) │
              │  search / sql / sum │
              └─────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  Governance Layer   │
              │  Guard + Audit + RL │
              └─────────────────────┘
```

### Cấu trúc thư mục

```
Day26-Track02-lab/
├── day26_mcp_a2a_lab.ipynb          # Notebook chính
├── README.md                         # Hướng dẫn
├── requirements.txt                  # Dependencies
├── mcp_server/
│   └── research_tools_server.py      # MCP + governance guard
├── agents/
│   ├── orchestrator/agent.py         # Điều phối chính
│   ├── search_agent/agent.py         # A2A :8001
│   ├── database_agent/agent.py       # A2A :8002
│   └── synthesis_agent/agent.py      # A2A :8003
├── lab_utils/
│   ├── governance/
│   │   ├── policy.json               # Ma trận capability
│   │   ├── guard.py                  # GovernanceGuard
│   │   ├── audit.py                  # Audit log JSONL
│   │   ├── adk_callbacks.py          # before_tool_callback
│   │   ├── models.py                 # Data models
│   │   └── rate_limit.py             # Rate limiter
│   ├── routing_tool.py               # suggest_routing
│   ├── semantic_router.py            # Bag-of-words router
│   ├── agent_registry.py             # In-memory registry
│   ├── env_setup.py                  # Load .env
│   └── full_flow.py                  # run_full_flow helper
└── scripts/
    ├── _lab_env.sh                   # Shared env setup
    ├── start_a2a_servers.sh          # Khởi động 3 specialist
    ├── start_adk_web.sh              # ADK Web UI :8000
    ├── start_capstone.sh             # A2A + ADK Web 1 lệnh
    ├── start_search_agent.sh         # Riêng search
    ├── start_database_agent.sh       # Riêng database
    ├── start_synthesis_agent.sh      # Riêng synthesis
    └── stop_a2a_servers.sh           # Dừng tất cả
```

---

## 3. Kế hoạch từng bước

### GIAI ĐOẠN 1: THIẾT LẬP MÔI TRƯỜNG (Module 0)

#### Bước 1.1 — Tạo & kích hoạt môi trường Conda

```bash
conda create -n pii-env python=3.12 -y
conda activate pii-env
```

- **Mục tiêu:** Môi trường Python 3.12 sạch, tách biệt khỏi base Anaconda.
- **Kiểm tra:** `conda info --envs` hiển thị `pii-env`.

#### Bước 1.2 — Cài đặt dependencies

```bash
pip install -r requirements.txt
```

- **Các gói chính:**
  - `google-adk[a2a]>=1.0.0` — Google ADK + A2A extension
  - `mcp>=1.0.0` — Model Context Protocol SDK
  - `uvicorn>=0.30.0` — ASGI server cho A2A HTTP
  - `httpx>=0.27.0` — HTTP client kiểm tra agent card
  - `numpy>=1.26.0` — Vector operations cho semantic router
  - `python-dotenv>=1.0.0` — Load biến môi trường
  - `jupyter>=1.0.0`, `ipykernel>=6.29.0` — Notebook
  - `cryptography>=46.0.7,<47.0.0` — Tương thích governance toolkit
- **Kiểm tra:** `pip list | grep google-adk` hiển thị version.

#### Bước 1.3 — Cấu hình biến môi trường

```bash
cp .env.example .env
# Thêm GOOGLE_API_KEY vào .env
export PYTHONPATH=$PWD
```

- **Mục tiêu:** API key Google AI Studio cho Gemini model.
- **Kiểm tra:** `python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('GOOGLE_API_KEY')[:10] + '...')"`

#### Bước 1.4 — Kiểm tra notebook kernel

- Mở `day26_mcp_a2a_lab.ipynb` trong Jupyter.
- Chọn kernel `pii-env`.
- Chạy cell `#VSC-f81fc85b` (pip install) và cell `#VSC-e9bbb8ce` (load env).
- **Kết quả mong đợi:** `✓ Môi trường sẵn sàng`.

---

### GIAI ĐOẠN 2: MCP SERVER (Module 1)

#### Bước 2.1 — Phân tích MCP server hiện có

- **File:** `mcp_server/research_tools_server.py`
- **3 tool hiện có:**
  1. `search_documents` — Tìm kiếm tài liệu nghiên cứu theo từ khóa
  2. `sql_query` — Thực thi SQL SELECT trên `agent_metrics`
  3. `summarize_text` — Tóm tắt văn bản thành gạch đầu dòng
- **Cơ chế governance:**
  - `_sql_query` chỉ cho phép bảng `AGENT_METRICS`
  - Mọi tool call đều qua `guard.authorize_mcp_tool()`
- **Transport:** stdio (dev local)

#### Bước 2.2 — 📝 Bài tập 1.1: Trả lời câu hỏi khám phá MCP

| # | Câu hỏi | Trả lời |
|---|---------|---------|
| 1 | Ba tool nào được expose? | `search_documents`, `sql_query`, `summarize_text` |
| 2 | `_sql_query` enforce governance thế nào? | Chỉ SELECT trên `AGENT_METRICS`; từ chối DDL/DML |
| 3 | Vì sao stdio khi dev local? | Đơn giản, không cần mở cổng, dễ debug |

#### Bước 2.3 — 📝 Bài tập 1.2: Thêm tool MCP thứ tư `count_words`

**Nhiệm vụ:** Mở rộng `research_tools_server.py`.

- [ ] **2.3.1** Thêm `count_words` vào `list_tools()` với `inputSchema`:
  ```python
  Tool(
      name="count_words",
      description="Đếm số từ trong một chuỗi văn bản.",
      inputSchema={
          "type": "object",
          "properties": {
              "text": {"type": "string", "description": "Văn bản cần đếm từ"},
          },
          "required": ["text"],
      },
  )
  ```
- [ ] **2.3.2** Triển khai hàm `_count_words(text: str) -> dict`:
  ```python
  def _count_words(text: str) -> dict:
      words = text.split()
      return {"word_count": len(words), "char_count": len(text)}
  ```
- [ ] **2.3.3** Thêm xử lý trong `call_tool()` cho `name == "count_words"`.
- [ ] **2.3.4** Thêm `"count_words"` vào `tool_filter` trong `agents/orchestrator/agent.py`.
- [ ] **2.3.5** Thêm policy cho `count_words` trong `lab_utils/governance/policy.json`:
  ```json
  "count_words": {
      "allowed": true,
      "data_classification": "internal"
  }
  ```
- [ ] **2.3.6** Test: chạy cell `#VSC-5bf7ddef` (Module 1) và xác nhận tool hoạt động.

---

### GIAI ĐOẠN 3: KHỞI ĐỘNG A2A SPECIALIST SERVERS (Module 0.5)

#### Bước 3.1 — Khởi động A2A servers

```bash
conda activate pii-env
export PYTHONPATH=$PWD
bash scripts/start_a2a_servers.sh
```

- **Kết quả mong đợi:** `search OK`, `database OK`, `synthesis OK`.

#### Bước 3.2 — Kiểm tra agent card

- Chạy cell `#VSC-4405416e` hoặc:
  ```bash
  curl http://localhost:8001/.well-known/agent-card.json
  curl http://localhost:8002/.well-known/agent-card.json
  curl http://localhost:8003/.well-known/agent-card.json
  ```
- **Kết quả mong đợi:** JSON response với `name`, `description`, `capabilities`.

---

### GIAI ĐOẠN 4: A2A GIAO THỨC (Module 2)

#### Bước 4.1 — Phân tích kiến trúc A2A

- **3 specialist agents:**
  | Agent | Cổng | Tool | Governance Callback |
  |-------|------|------|---------------------|
  | `search_agent` | 8001 | `search_web` | `before_tool_callback` + `before_agent_callback` |
  | `database_agent` | 8002 | `run_sql_query` | `before_tool_callback` + `before_agent_callback` |
  | `synthesis_agent` | 8003 | `synthesize_report` | `before_tool_callback` + `before_agent_callback` |

- **Orchestrator tiêu thụ qua `RemoteA2aAgent`:**
  ```python
  search_specialist = RemoteA2aAgent(
      name="search_agent",
      description="Tìm kiếm tài liệu và web...",
      agent_card="http://localhost:8001/.well-known/agent-card.json",
  )
  ```

#### Bước 4.2 — 📝 Bài tập 2.1: So sánh A2A vs Sub-Agent Local

| Tiêu chí | A2A (Remote) | Sub-Agent Local |
|----------|-------------|------------------|
| Triển khai | Process riêng, cổng HTTP | Cùng process, import trực tiếp |
| Hiệu năng | Network overhead (HTTP) | Gọi hàm trực tiếp, nhanh hơn |
| Cô lập state | State riêng biệt hoàn toàn | Có thể chia sẻ state |
| Phù hợp khi | Microservices, scale độc lập | Monolith, prototype nhanh |

**Thảo luận:** Chọn A2A khi cần scale độc lập từng agent, triển khai đa ngôn ngữ, hoặc cần cô lập lỗi. Chọn sub-agent local khi cần hiệu năng tối đa và chia sẻ state.

---

### GIAI ĐOẠN 5: AGENTIC ROUTING (Module 3)

#### Bước 5.1 — Phân tích Semantic Router hiện có

- **File:** `lab_utils/semantic_router.py`
- **Cơ chế:** Bag-of-words + cosine similarity (không cần embedding API)
- **3 agent capability đã đăng ký:**
  | Agent | Tags |
  |-------|------|
  | `search_agent` | search, web, documents |
  | `database_agent` | sql, metrics, database |
  | `synthesis_agent` | summary, report, synthesis |

#### Bước 5.2 — Test semantic routing

- Chạy cell `#VSC-1932614d` trong notebook.
- **Kết quả mong đợi:** Router định tuyến đúng cho các truy vấn test.

#### Bước 5.3 — 📝 Bài tập 3.1: Xây dựng Fallback Chain

- [ ] **5.3.1** Thêm phương thức `route_with_chain()` vào class `SemanticRouter` trong `lab_utils/semantic_router.py`:
  ```python
  def route_with_chain(self, request: str, chain: list[str]) -> str:
      """Thử route chính; nếu điểm < ngưỡng, đi theo chuỗi fallback."""
      candidates = self.route(request, top_k=1)
      if candidates and candidates[0][1] >= self.threshold:
          return candidates[0][0]
      for fallback in chain:
          if fallback in [a.name for a in self.agents]:
              return fallback
      return chain[-1] if chain else "orchestrator"
  ```
- [ ] **5.3.2** Test với chain: `["search_agent", "database_agent", "orchestrator"]`.

#### Bước 5.4 — Kiểm tra Agent Registry

- Chạy cell `#VSC-cdcf738e`.
- **Kết quả mong đợi:** Danh sách agent đã đăng ký với trạng thái healthy.

---

### GIAI ĐOẠN 6: DEMO FULL LUỒNG (Module 4)

#### Bước 6.1 — Chạy full flow A2A

- Chạy cell `#VSC-855659b3` (kiểm tra servers).
- Chạy cell `#VSC-104cb33b` (Ví dụ 1 — A2A search delegation).
- **Prompt:** `"Transfer sang search_agent để tìm kiếm web về multi-agent orchestration."`
- **Kết quả mong đợi:** Orchestrator → transfer → search_agent → kết quả.

#### Bước 6.2 — Chạy full flow MCP + A2A

- Chạy cell `#VSC-5b80e462` (Ví dụ 2 — MCP multi-tool).
- **Prompt:** Sử dụng `search_documents`, `sql_query`, tổng hợp báo cáo.
- **Kết quả mong đợi:** Orchestrator gọi MCP tools → tổng hợp.

---

### GIAI ĐOẠN 7: CAPSTONE ADK WEB UI (Module 4 — Capstone)

#### Bước 7.1 — Khởi động capstone

```bash
bash scripts/start_capstone.sh
```

- **Kết quả mong đợi:** 
  - A2A servers :8001, :8002, :8003 đang chạy
  - ADK Web UI tại http://localhost:8000

#### Bước 7.2 — 📝 Chạy 5 prompt W1–W5

| # | Prompt | Giao thức | Kỳ vọng |
|---|--------|-----------|---------|
| **W1** | `Tôi cần tìm web về multi-agent orchestration. Hãy transfer_to_agent sang search_agent và trả kết quả.` | A2A | search_agent → text |
| **W2** | `Bước 1: dùng search_documents tìm MCP. Bước 2: dùng sql_query SELECT * FROM agent_metrics. Bước 3: tóm tắt báo cáo ngắn.` | MCP | search_documents + sql_query |
| **W3** | `Ủy quyền synthesis_agent tổng hợp báo cáo executive từ các findings về MCP và A2A.` | A2A | synthesis_agent |
| **W4** | `Gọi suggest_routing rồi giải thích bạn sẽ chọn agent nào: "SELECT độ trễ trung bình từ agent_metrics"` | Tool | suggest_routing → database_agent |
| **W5** | `DROP TABLE agent_metrics` | Governance | Bị chặn — blocked/deny |

#### Bước 7.3 — 📝 Điền kết quả vào cell `#VSC-abe1600b`

- [ ] Ghi lại agents_involved, outcome, notes cho từng prompt.
- [ ] Chụp screenshot ADK Web (ít nhất W1 và W2).

#### Bước 7.4 — Kiểm tra audit log

```bash
tail -5 logs/governance_audit.jsonl
```

#### Bước 7.5 — Kiểm tra trace trong ADK Web

- Mở tab **Trace** bên phải giao diện ADK Web.
- Xác nhận `transfer_to_agent`, MCP calls, A2A events hiển thị.

---

### GIAI ĐOẠN 8: GOVERNANCE & BẢO MẬT (Module 5)

#### Bước 8.1 — Phân tích hệ thống governance

- **File chính:**
  - `lab_utils/governance/policy.json` — Ma trận capability
  - `lab_utils/governance/guard.py` — `GovernanceGuard` class
  - `lab_utils/governance/audit.py` — `AuditLogger`
  - `lab_utils/governance/adk_callbacks.py` — `before_tool_callback`
  - `lab_utils/governance/rate_limit.py` — `RateLimiter`
  - `lab_utils/governance/models.py` — Data models

- **Luồng kiểm soát:**
  ```
  Request → GovernanceGuard → [ALLOW | DENY | HITL_REQUIRED]
                  ↓
           AuditLogger (timestamp, actor, I/O)
                  ↓
           MCP tool / A2A dispatch
  ```

#### Bước 8.2 — 📝 Bài tập 5.1: Thiết kế chính sách Governance

- [ ] **8.2.1** Viết ma trận capability cho 4 agent:

| Agent | Được phép gọi tool | Bị chặn | Rate limit | HITL trigger |
|-------|-------------------|---------|------------|--------------|
| `orchestrator` | MCP: search_documents, sql_query, summarize_text, count_words; A2A: dispatch tới 3 specialist | MCP từ agent khác | 30/phút | PII trong SQL, thiếu trace_id |
| `search_agent` | `search_web` | write, delete, send_email | 30/phút | Không |
| `database_agent` | `run_sql_query` (chỉ SELECT) | DDL, DML, TRUNCATE | 30/phút | PII trong SQL |
| `synthesis_agent` | `synthesize_report` | Thu thập dữ liệu mới | 30/phút | Không |

- **Giới hạn toàn cục:**
  - Tối đa 50 tool calls/task
  - Tối đa 300 giây thực thi
  - Trần chi phí $10.00

#### Bước 8.3 — 📝 Bài tập 5.2: Mở rộng chính sách governance

- [ ] **8.3.1** Mở `lab_utils/governance/policy.json`, thêm `synthesis_agent` vào `allowed_targets` của orchestrator.
- [ ] **8.3.2** Thêm rule chặn từ khóa `password` trong `search_documents` (trong `guard.py`).
- [ ] **8.3.3** Chạy cell `#VSC-66f902cc` — xác nhận audit log ghi đủ sự kiện `deny` / `hitl_required`.
- [ ] **8.3.4** *(Nâng cao)* Viết test đảm bảo caller không hợp lệ không mở được kết nối MCP.

#### Bước 8.4 — Chạy governance test

- Chạy cell `#VSC-66f902cc` (Module 5).
- **Kết quả mong đợi:**
  - `DROP TABLE` → DENY
  - `SELECT hợp lệ` → ALLOW
  - `orchestrator → search_agent` → ALLOW
  - `orchestrator → email_agent` → DENY
  - Không có `trace_id` → HITL_REQUIRED
  - PII trong SQL → HITL_REQUIRED

---

### GIAI ĐOẠN 9: STATE, OBSERVABILITY & DISTRIBUTED TRACING (Module 5)

#### Bước 9.1 — Tìm hiểu quản lý state

- **File tham khảo:** Cell `#VSC-1d94ec62` (ví dụ `track_cost`).
- **Mẫu state trong ADK:** `tool_context.state` cho phép chia sẻ dữ liệu giữa các lượt gọi.

#### Bước 9.2 — Cấu hình distributed tracing

- **Cơ chế:** `RunConfig.custom_metadata` truyền `trace_id` qua ranh giới A2A.
- **Trong ADK Web:** `adk_callbacks.py` tự động sinh `trace_id` nếu chưa có.
- **Kiểm tra:** Tab Trace trong ADK Web hiển thị toàn bộ luồng.

#### Bước 9.3 — Các metric cần theo dõi

| Metric | Mục đích | Nguồn |
|--------|----------|-------|
| `tasks_completed` / `tasks_failed` | Độ tin cậy | Audit log |
| `avg_task_duration` | Độ trễ | Trace |
| `tool_call_count` | Phát hiện chạy vô hạn | Governance guard |
| `cost_per_task` | Phân bổ ngân sách | Governance guard |
| `queue_depth` | Lập kế hoạch năng lực | Rate limiter |

---

### GIAI ĐOẠN 10: CAPSTONE CHECKLIST & MỞ RỘNG

#### Bước 10.1 — Hoàn thiện capstone checklist

- [ ] MCP server với 3+ tool (stdio spawn tự động)
- [ ] Agent registry có health check
- [ ] Semantic router + `suggest_routing` tool
- [ ] Search agent expose `to_a2a()` :8001
- [ ] Database agent expose `to_a2a()` :8002
- [ ] Synthesis agent expose `to_a2a()` :8003
- [ ] Orchestrator tiêu thụ cả ba qua `RemoteA2aAgent`
- [ ] ADK Web demo 5 prompt W1–W5 + ghi kết quả
- [ ] Trace ID tự sinh trong ADK Web
- [ ] Governance policy ghi audit

#### Bước 10.2 — Thử thách mở rộng (tùy chọn)

- [ ] **Transport SSE:** Triển khai MCP server với FastAPI + uvicorn cổng 8080
- [ ] **Tải đồng thời:** Gửi 5 request và quan sát phân phối routing
- [ ] **Embedding router:** Thay bag-of-words bằng `text-embedding-004` (Google AI)
- [ ] **Cổng HITL:** Tạm dừng trước hành động vượt $10 chi phí API

---

### GIAI ĐOẠN 11: TỔNG KẾT & NỘP BÀI

#### Bước 11.1 — Hoàn thiện notebook

- [ ] Tất cả cell đã được thực thi thành công
- [ ] Kết quả W1–W5 đã điền trong cell `#VSC-abe1600b`
- [ ] Screenshot ADK Web (W1, W2) đã chèn

#### Bước 11.2 — Kiểm tra audit log

```bash
tail -20 logs/governance_audit.jsonl
```

#### Bước 11.3 — Dừng servers

```bash
bash scripts/stop_a2a_servers.sh
```

#### Bước 11.4 — Nộp bài

- [ ] File notebook `.ipynb` đã hoàn chỉnh
- [ ] File `report.md` đã điền đầy đủ thông tin
- [ ] File `work_plan.md` (file này)
- [ ] Screenshot chụp màn hình ADK Web
- [ ] Audit log mẫu (trích từ `logs/governance_audit.jsonl`)

---

## 4. Bảng phân công & tiến độ

| Giai đoạn | Bước | Nội dung | Thời lượng dự kiến | Trạng thái |
|-----------|------|----------|-------------------|------------|
| 1 | 1.1–1.4 | Thiết lập môi trường | 15 phút | ⬜ Chưa bắt đầu |
| 2 | 2.1–2.3 | MCP Server & bài tập 1.1, 1.2 | 25 phút | ⬜ Chưa bắt đầu |
| 3 | 3.1–3.2 | Khởi động A2A servers | 10 phút | ⬜ Chưa bắt đầu |
| 4 | 4.1–4.2 | A2A Protocol & bài tập 2.1 | 10 phút | ⬜ Chưa bắt đầu |
| 5 | 5.1–5.4 | Semantic Router & bài tập 3.1 | 15 phút | ⬜ Chưa bắt đầu |
| 6 | 6.1–6.2 | Demo full luồng | 10 phút | ⬜ Chưa bắt đầu |
| 7 | 7.1–7.5 | Capstone ADK Web & 5 prompt | 20 phút | ⬜ Chưa bắt đầu |
| 8 | 8.1–8.4 | Governance & bài tập 5.1, 5.2 | 20 phút | ⬜ Chưa bắt đầu |
| 9 | 9.1–9.3 | State & Observability | 10 phút | ⬜ Chưa bắt đầu |
| 10 | 10.1–10.2 | Checklist & mở rộng | 15 phút | ⬜ Chưa bắt đầu |
| 11 | 11.1–11.4 | Tổng kết & nộp bài | 10 phút | ⬜ Chưa bắt đầu |
| **Tổng** | | | **~2 giờ 40 phút** | |

---

## 5. Tiêu chí đánh giá hoàn thành

| # | Tiêu chí | Trọng số | Cách kiểm tra |
|---|----------|---------|---------------|
| 1 | Môi trường hoạt động | Bắt buộc | Cell Module 0 output `✓ Môi trường sẵn sàng` |
| 2 | MCP server 3+ tool | 15% | Cell `#VSC-5bf7ddef` + `count_words` mới |
| 3 | A2A servers khởi động | 15% | `curl` 3 agent card trả về JSON |
| 4 | Semantic router đúng | 10% | Cell `#VSC-1932614d` phân loại đúng |
| 5 | Full flow A2A + MCP | 15% | Cell `#VSC-104cb33b` và `#VSC-5b80e462` |
| 6 | ADK Web 5 prompt | 20% | Kết quả W1–W5 + screenshot |
| 7 | Governance audit | 15% | Cell `#VSC-66f902cc` + `logs/governance_audit.jsonl` |
| 8 | Bài tập mở rộng | 10% | `count_words`, `route_with_chain`, policy mở rộng |

---

## 6. Rủi ro & giải pháp

| Rủi ro | Xác suất | Tác động | Giải pháp |
|--------|---------|----------|-----------|
| Thiếu `GOOGLE_API_KEY` | Trung bình | Cao — không gọi được Gemini | Kiểm tra `.env` trước khi chạy |
| Xung đột package cryptography | Thấp | Trung bình | Đã ghim `cryptography>=46.0.7,<47.0.0` |
| A2A server không khởi động | Trung bình | Cao | Kiểm tra cổng 8001–8003 còn trống; xem log trong `logs/` |
| Notebook kernel sai | Thấp | Trung bình | Luôn chọn kernel `pii-env` |
| ADK Web không hiển thị trace | Trung bình | Thấp | Kiểm tra `before_agent_callback` đã gán; xem log |

---

> **Ghi chú:** File này là kế hoạch chi tiết. Tiến độ thực tế sẽ được cập nhật trong quá trình thực hiện lab. Mọi câu hỏi và thảo luận được ghi trong `report.md`.
