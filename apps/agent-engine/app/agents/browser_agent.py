"""Browser agent (Flow B) — real Playwright automation.

The observe → decide → safety → execute loop drives a live Chromium page:

    open_browser -> observer -> decision -> safety -> execute -> observer -> ...

`decision` (agents/reasoning_agent.py) and `safety` (agents/safety_agent.py) live
elsewhere; this module owns the three nodes that touch the browser. The page is
kept in an in-process session registry keyed by thread_id (see browser_tool).
"""
from __future__ import annotations

from app.graph.graph_state import AgentState
from app.tools.builtin.browser_tool import get_or_create_session, get_session


async def open_browser_node(state: AgentState) -> dict:
    """Launch a session (if needed) and open the user's URL."""
    url = state.get("url")
    if not url:
        return {"error": "No URL to open for browser automation."}
    try:
        session = await get_or_create_session(state["thread_id"])
        await session.open(url)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Couldn't open {url}: {type(exc).__name__}: {exc}"}
    return {"session_id": state["thread_id"], "current_url": url}


async def observer_node(state: AgentState) -> dict:
    """Read the current page into a structured observation."""
    session = get_session(state["thread_id"])
    if session is None:
        return {"error": "Browser session was lost."}
    try:
        observation = await session.observe()
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Couldn't read the page: {type(exc).__name__}: {exc}"}
    return {"observation": observation, "current_url": observation.get("url")}


async def execute_node(state: AgentState) -> dict:
    """Perform the approved action against the live page."""
    if state.get("approval_decision") == "rejected":
        return {
            "final_answer": (
                "No problem — I cancelled that and didn't complete the action."
            )
        }

    session = get_session(state["thread_id"])
    if session is None:
        return {"error": "Browser session was lost."}

    action = state.get("next_action") or {}
    kind = action.get("type")
    agent_id = action.get("agent_id")
    try:
        if kind == "click" and agent_id is not None:
            result = await session.click(int(agent_id))
        elif kind == "type" and agent_id is not None:
            result = await session.type(int(agent_id), action.get("value", ""))
            result += "; " + await session.press_enter()
        elif kind == "scroll":
            result = await session.scroll()
        elif kind == "extract":
            result = "read the current page"
        else:
            result = f"skipped unsupported action '{kind}'"
    except Exception as exc:  # noqa: BLE001
        step = state.get("step_index", 0) + 1
        return {"error": f"Action failed: {type(exc).__name__}: {exc}", "step_index": step}

    collected = list(state.get("collected") or [])
    collected.append({"summary": f"{action.get('description', kind)} → {result}"})
    return {
        "step_index": state.get("step_index", 0) + 1,
        "collected": collected,
        "approval_decision": None,  # reset for the next loop iteration
    }
