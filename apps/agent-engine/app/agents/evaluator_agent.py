"""Reviewer / evaluator node.

Produces the final assistant message and, for browser runs, tears down the live
Playwright session. For Flow A it's a light pass-through of the synthesized
answer; for Flow B it surfaces the Decision agent's final answer (or a summary of
what was collected) and closes the browser.
"""
from __future__ import annotations

from langchain_core.messages import AIMessage

from app.graph.graph_state import AgentState
from app.tools.builtin.browser_tool import close_session


async def reviewer_node(state: AgentState) -> dict:
    if state.get("error"):
        answer = f"I couldn't complete that: {state['error']}"
    elif state.get("final_answer"):
        answer = state["final_answer"]
    else:
        # Browser run that ended without an explicit final answer.
        action = state.get("next_action") or {}
        if action.get("type") == "final" and action.get("answer"):
            answer = action["answer"]
        else:
            steps = state.get("collected") or []
            done = "\n".join(f"• {s.get('summary')}" for s in steps)
            answer = (
                "Here's what I did:\n" + done if done else "I wasn't able to make progress."
            )

    # Always release the browser if this run opened one.
    if state.get("session_id"):
        try:
            await close_session(state["session_id"])
        except Exception:  # noqa: BLE001 — cleanup must not fail the run
            pass

    return {"final_answer": answer, "messages": [AIMessage(content=answer)]}
