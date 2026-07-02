"""Callback ADK tích hợp governance vào orchestrator và specialist agents."""

from __future__ import annotations

import json
import uuid
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

from lab_utils.governance.guard import get_guard
from lab_utils.free_llm_man import get_tier_manager

# Tool nội bộ ADK dùng để chuyển giao giữa agent.
_TRANSFER_TOOL_NAMES = frozenset({
    "transfer_to_agent",
    "request_task",
})


def _extract_actor_id(ctx: ToolContext | CallbackContext) -> str:
    inv = getattr(ctx, "_invocation_context", None)
    if inv and getattr(inv, "agent", None) and getattr(inv.agent, "name", None):
        return str(inv.agent.name)
    name = getattr(ctx, "agent_name", None)
    if name:
        return str(name)
    return "orchestrator"


def _extract_trace_id(ctx: ToolContext | CallbackContext) -> str | None:
    state = getattr(ctx, "state", None)
    if state is not None:
        tid = state.get("trace_id") or state.get("governance_trace_id")
        if tid:
            return str(tid)

    inv = getattr(ctx, "_invocation_context", None)
    if inv and getattr(inv, "run_config", None):
        metadata = inv.run_config.custom_metadata or {}
        tid = metadata.get("trace_id")
        if tid:
            return str(tid)

    session = getattr(ctx, "session", None)
    if session and getattr(session, "state", None):
        tid = session.state.get("trace_id") or session.state.get("governance_trace_id")
        if tid:
            return str(tid)

    return None


def _extract_task_id(ctx: ToolContext | CallbackContext) -> str:
    state = getattr(ctx, "state", None)
    if state is not None and state.get("task_id"):
        return str(state["task_id"])
    return "default"


async def governance_before_tool_callback(
    tool: BaseTool | None = None,
    args: dict[str, Any] | None = None,
    tool_context: ToolContext | None = None,
    **kwargs: Any,
) -> dict[str, Any] | None:
    """Chặn hoặc yêu cầu HITL trước khi thực thi tool MCP / A2A.

    Trả về dict để bỏ qua tool và dùng kết quả thay thế.
    Trả về None để cho phép thực thi bình thường.
    """
    tool = tool or kwargs.get("tool")
    args = args if args is not None else kwargs.get("args", {})
    tool_context = tool_context or kwargs.get("tool_context")
    if tool is None or tool_context is None:
        return None

    guard = get_guard()
    actor_id = _extract_actor_id(tool_context)
    trace_id = _extract_trace_id(tool_context)
    task_id = _extract_task_id(tool_context)
    tool_name = tool.name

    # A2A delegation qua transfer_to_agent / request_task (tool nội bộ ADK)
    if tool_name in _TRANSFER_TOOL_NAMES:
        target = args.get("agent_name") or args.get("target_agent") or args.get("name")
        if target:
            decision = guard.authorize_a2a_dispatch(
                source_agent=actor_id,
                target_agent=str(target),
                task_summary=json.dumps(args, ensure_ascii=False)[:200],
                trace_id=trace_id,
                task_id=task_id,
            )
            if decision.blocked:
                return {
                    "status": "blocked",
                    "governance": decision.verdict.value,
                    "reason": decision.reason,
                }
            if decision.needs_approval:
                return {
                    "status": "hitl_required",
                    "governance": decision.verdict.value,
                    "reason": decision.reason,
                    "message": "Hành động cần phê duyệt của người trước khi tiếp tục.",
                }
        # Dispatch đã được phép — không kiểm tra authorize_agent_tool (orchestrator
        # không có allowed_tools; nếu fall-through sẽ deny transfer_to_agent).
        return None

    # MCP tools (tên tool khớp policy)
    mcp_tools = guard.policy["connections"]["mcp"]["research-tools"].get("tools", {})
    if tool_name in mcp_tools:
        decision = guard.authorize_mcp_tool(
            actor_id=actor_id,
            tool_name=tool_name,
            arguments=args,
            trace_id=trace_id,
            task_id=task_id,
        )
        if decision.blocked:
            return {
                "status": "blocked",
                "governance": decision.verdict.value,
                "reason": decision.reason,
            }
        if decision.needs_approval:
            return {
                "status": "hitl_required",
                "governance": decision.verdict.value,
                "reason": decision.reason,
            }
        return None

    # Tool trên A2A specialist (chỉ agent có allowed_tools — không áp orchestrator)
    a2a_agents = guard.policy["connections"]["a2a"]
    agent_policy = a2a_agents.get(actor_id, {})
    if agent_policy.get("allowed_tools"):
        decision = guard.authorize_agent_tool(
            actor_id=actor_id,
            tool_name=tool_name,
            arguments=args,
            trace_id=trace_id,
            task_id=task_id,
        )
        if decision.blocked:
            return {
                "status": "blocked",
                "governance": decision.verdict.value,
                "reason": decision.reason,
            }
        if decision.needs_approval:
            return {
                "status": "hitl_required",
                "governance": decision.verdict.value,
                "reason": decision.reason,
            }

    return None


async def governance_before_agent_callback(
    *args: Any,
    callback_context: CallbackContext | None = None,
    **kwargs: Any,
) -> None:
    """Khởi tạo state governance và đồng bộ trace_id từ RunConfig.

    ADK gọi với keyword ``callback_context=``; chấp nhận thêm positional
    để tương thích các phiên bản / process uvicorn cũ.
    """
    ctx = callback_context
    if ctx is None and args:
        ctx = args[0]
    if ctx is None:
        ctx = kwargs.get("callback_context")
    if ctx is None:
        return None

    state = ctx.state
    if "governance_tool_count" not in state:
        state["governance_tool_count"] = 0
    if "governance_total_cost_usd" not in state:
        state["governance_total_cost_usd"] = 0.0

    inv = getattr(ctx, "_invocation_context", None)
    if inv and getattr(inv, "run_config", None):
        metadata = inv.run_config.custom_metadata or {}
        trace_id = metadata.get("trace_id")
        if trace_id:
            state["trace_id"] = trace_id
            state["governance_trace_id"] = trace_id
        task_id = metadata.get("task_id")
        if task_id:
            state["task_id"] = task_id

    # ADK Web không truyền RunConfig.custom_metadata — tự sinh trace_id
    if not state.get("trace_id"):
        tid = str(uuid.uuid4())
        state["trace_id"] = tid
        state["governance_trace_id"] = tid
    if not state.get("task_id"):
        state["task_id"] = f"task-{str(state['trace_id'])[:8]}"

    # ── Free Tier tracking ──────────────────────────────────────────
    tier_mgr = get_tier_manager()
    ok, msg = tier_mgr.check_limits()
    if not ok:
        # Ghi cảnh báo vào state thay vì raise (tránh crash ADK flow)
        state["tier_blocked"] = True
        state["tier_blocked_reason"] = msg
        import warnings
        warnings.warn(f"Free Tier limit: {msg}")
    else:
        state["tier_blocked"] = False
        # Ghi nhận LLM call ước tính (mỗi agent invocation ≈ 1 LLM call)
        tier_mgr.record_call(tokens=0)
        state["governance_tool_count"] = state.get("governance_tool_count", 0) + 1

    return None
