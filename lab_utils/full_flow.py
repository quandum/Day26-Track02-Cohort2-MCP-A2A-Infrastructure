"""Helper chạy full luồng orchestrator → A2A + MCP cho notebook lab."""

from __future__ import annotations

import sys
import uuid
import warnings
from pathlib import Path
from typing import Any

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lab_utils.free_llm_man import get_tier_manager, print_tier_status

AGENT_CARDS = {
    "search_agent": "http://localhost:8001/.well-known/agent-card.json",
    "database_agent": "http://localhost:8002/.well-known/agent-card.json",
    "synthesis_agent": "http://localhost:8003/.well-known/agent-card.json",
}


def check_a2a_servers(timeout: float = 3.0) -> tuple[bool, list[str]]:
    """Kiểm tra A2A specialist đang chạy."""
    errors: list[str] = []
    for name, url in AGENT_CARDS.items():
        try:
            response = httpx.get(url, timeout=timeout)
            response.raise_for_status()
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    return len(errors) == 0, errors


async def run_full_flow(
    user_message: str,
    *,
    trace_id: str | None = None,
    user_id: str = "student",
    app_name: str = "day26_lab",
    verbose: bool = True,
) -> dict[str, Any]:
    """Chạy full luồng: orchestrator → A2A specialists + MCP tools.

    Returns:
        dict với keys: trace_id, events, final_answer, authors
    """
    ok, errors = check_a2a_servers()
    if not ok:
        raise RuntimeError(
            "A2A servers chưa sẵn sàng. Chạy Module 0.5 trước.\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    # Kiểm tra free tier limits trước khi gọi Gemini API
    tier = get_tier_manager()
    tier_ok, tier_msg = tier.check_limits()
    if not tier_ok:
        raise RuntimeError(f"Free tier limit reached: {tier_msg}")
    if verbose:
        print_tier_status()
        warn = tier.warn_if_near_limit()
        if warn:
            print(f"  {warn}")

    warnings.filterwarnings("ignore", category=UserWarning)

    from google.adk.agents.run_config import RunConfig
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    from agents.orchestrator.agent import root_agent

    trace_id = trace_id or str(uuid.uuid4())
    runner = InMemoryRunner(agent=root_agent, app_name=app_name)
    session = await runner.session_service.create_session(
        user_id=user_id,
        app_name=app_name,
        state={
            "trace_id": trace_id,
            "governance_trace_id": trace_id,
            "task_id": f"task-{trace_id[:8]}",
        },
    )

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_message)],
    )

    events: list[dict[str, str]] = []
    authors: set[str] = set()
    final_answer = ""

    run_config = RunConfig(
        custom_metadata={
            "trace_id": trace_id,
            "task_id": f"task-{trace_id[:8]}",
            "lab": "day26",
            "user_tier": "student",
        }
    )

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=content,
        run_config=run_config,
    ):
        author = getattr(event, "author", "unknown")
        authors.add(author)
        if event.content and event.content.parts:
            text = event.content.parts[0].text or ""
            if text.strip():
                events.append({"author": author, "text": text})
                if verbose:
                    preview = text[:300] + ("..." if len(text) > 300 else "")
                    print(f"[{author}] {preview}")
                final_answer = text

    return {
        "trace_id": trace_id,
        "events": events,
        "final_answer": final_answer,
        "authors": sorted(authors),
    }


def print_flow_summary(result: dict[str, Any]) -> None:
    """In tóm tắt kết quả full luồng."""
    print("\n" + "=" * 60)
    print(f"Trace ID : {result['trace_id']}")
    print(f"Agents   : {', '.join(result['authors']) or '—'}")
    print(f"Sự kiện  : {len(result['events'])} lượt")
    print("=" * 60)
    print(result["final_answer"])
