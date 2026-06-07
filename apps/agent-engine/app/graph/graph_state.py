"""Shared LangGraph state.

One TypedDict that every node reads and writes. The browser/HITL fields are
declared now (so the schema is stable) but only exercised by Flow B in a later
phase. The spine (Flow A) uses: messages, task, url, mode, page_text,
final_answer, error.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, TypedDict

from langgraph.graph.message import add_messages

Mode = Literal["chat", "vision", "analyze", "browser"]


class AgentState(TypedDict, total=False):
    # --- identity ---
    run_id: str
    thread_id: str
    user_id: Optional[str]
    site_origin: Optional[str]

    # --- conversation / task ---
    messages: Annotated[list, add_messages]
    task: str
    mode: Mode
    url: Optional[str]
    history: list[dict]        # prior [{role, content}] turns for context
    images: list[str]          # attached image data URLs (vision)

    # --- Flow A: URL analyze ---
    page_text: Optional[str]
    page_title: Optional[str]

    # --- Flow B: browser (declared now, used later) ---
    plan: list[str]
    step_index: int
    session_id: Optional[str]
    current_url: Optional[str]
    observation: Optional[dict[str, Any]]
    next_action: Optional[dict[str, Any]]
    pending_approval: Optional[dict[str, Any]]
    approval_decision: Optional[Literal["approved", "rejected"]]
    collected: list[dict[str, Any]]

    # --- result ---
    final_answer: Optional[str]
    error: Optional[str]


def initial_state(
    *,
    run_id: str,
    thread_id: str,
    task: str,
    user_id: str | None = None,
    site_origin: str | None = None,
    history: list[dict] | None = None,
    images: list[str] | None = None,
) -> AgentState:
    """Build a fresh state for a new run."""
    return {
        "run_id": run_id,
        "thread_id": thread_id,
        "user_id": user_id,
        "site_origin": site_origin,
        "messages": [],
        "task": task,
        "mode": "chat",
        "url": None,
        "history": history or [],
        "images": images or [],
        "page_text": None,
        "page_title": None,
        "plan": [],
        "step_index": 0,
        "session_id": None,
        "current_url": None,
        "observation": None,
        "next_action": None,
        "pending_approval": None,
        "approval_decision": None,
        "collected": [],
        "final_answer": None,
        "error": None,
    }
