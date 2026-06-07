"""Safety-Guard node — the human-in-the-loop gate.

Sits between Decision and Executor. It classifies the proposed action and, when
risky, records a `pending_approval` payload describing what needs sign-off. The
graph is compiled with `interrupt_before=["execute"]`, so execution always
pauses before the Executor; the streaming layer then decides:
  - pending_approval set  -> ask the user (Continue / Cancel)
  - pending_approval None -> safe, auto-continue without bothering the user

The Continue/Cancel choice is written back to `approval_decision` before the run
resumes (see graph_streaming.resume_and_stream), and the Executor reads it.

We use static `interrupt_before` rather than the dynamic `interrupt()` because
the latter needs a runnable context that isn't reliably propagated on
Python 3.10.
"""
from __future__ import annotations

from app.graph.graph_state import AgentState
from app.guards.safety_guard import classify_action


def safety_node(state: AgentState) -> dict:
    action = state.get("next_action") or {}
    verdict = classify_action(action)

    if not verdict.risky:
        # Safe → auto-approve; the pause before execute will be auto-resumed.
        return {"pending_approval": None, "approval_decision": "approved"}

    return {
        "pending_approval": {
            "action": action.get("description", "this action"),
            "risk": verdict.category,
            "risk_label": verdict.label,
            "reason": verdict.reason,
            "url": state.get("url"),
        },
        "approval_decision": None,
    }
