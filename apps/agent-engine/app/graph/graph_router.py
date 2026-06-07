"""Conditional edge functions for the graph.

Kept separate from graph_builder so routing logic is easy to find and unit-test.
"""
from __future__ import annotations

from app.config.settings import settings
from app.graph.graph_state import AgentState


def route_after_supervisor(state: AgentState) -> str:
    """Pick the entry node for the chosen mode."""
    mode = state.get("mode")
    if mode == "browser":
        return "browser"
    if mode == "analyze":
        return "fetch"
    return "respond"  # chat + vision


def route_after_decision(state: AgentState) -> str:
    """Decision either finishes the task or proposes an action to gate + run."""
    action = state.get("next_action") or {}
    if state.get("error"):
        return "reviewer"
    return "reviewer" if action.get("type") == "final" else "safety"


def route_after_execute(state: AgentState) -> str:
    """Continue the observe→act loop, or stop (rejected / error / step budget)."""
    if state.get("error") or state.get("approval_decision") == "rejected":
        return "reviewer"
    if state.get("step_index", 0) >= settings.BROWSER_MAX_STEPS:
        return "reviewer"
    return "observer"
