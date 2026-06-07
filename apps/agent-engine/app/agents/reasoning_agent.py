"""Decision agent (Flow B).

Given the task and the current page observation, the LLM picks ONE next action.
Returns a structured action dict that the Safety-Guard classifies and the
Executor performs:

    {"type": "click|type|scroll|extract|final",
     "agent_id": <int or null>,   # which interactive element (from observation)
     "value": <str or null>,       # text to type
     "answer": <str or null>,      # final answer when type == "final"
     "description": <str>,         # human-readable, e.g. "Click 'Place Order'"
     "reasoning": <str>}
"""
from __future__ import annotations

import json
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from app.graph.graph_state import AgentState
from app.llms.providers.groq_provider import get_llm

SYSTEM_PROMPT = """You are a careful web-browsing agent. You see the current page \
(its full visible TEXT and a numbered list of interactive elements) and must \
choose the SINGLE next action that makes progress on the user's task.

Respond with ONE JSON object and nothing else:
{"type": "click|type|scroll|final",
 "agent_id": <number from the elements list, or null>,
 "value": "<text to type, or null>",
 "answer": "<your final answer to the user, only when type=final>",
 "description": "<short human-readable action, e.g. Click 'Add to cart'>",
 "reasoning": "<one sentence why>"}

Rules:
- The PAGE TEXT shown to you is the real, current page. If it already contains \
enough to answer the task, choose "final" NOW and put the answer in "answer". Do \
not keep browsing once you can answer.
- Only "click"/"type"/"scroll" when you genuinely need more of the page or a \
different page. "type" needs an input element's agent_id AND a value.
- Never repeat the same action twice in a row; if it didn't help, choose "final".
- Never invent agent_ids that are not in the list.
- For anything that spends money, deletes, submits sensitive data, or changes an \
account, still choose the action — a separate safety check will ask the human \
before it runs. Make the description explicit (e.g. "Click 'Place order' (pays ₹297)")."""


def _format_observation(state: AgentState) -> str:
    obs = state.get("observation") or {}
    elements = obs.get("elements") or []
    el_lines = "\n".join(
        f"  [{e['id']}] ({e['kind']}) {e['text'] or '<no label>'}" for e in elements
    )
    history = state.get("collected") or []
    hist_lines = "\n".join(f"  - {h.get('summary', h)}" for h in history[-6:])
    return (
        f"TASK: {state.get('task')}\n\n"
        f"CURRENT URL: {obs.get('url')}\n"
        f"PAGE TITLE: {obs.get('title')}\n\n"
        f"PAGE TEXT (truncated):\n{obs.get('text', '')[:2500]}\n\n"
        f"INTERACTIVE ELEMENTS:\n{el_lines or '  (none)'}\n\n"
        f"ACTIONS SO FAR:\n{hist_lines or '  (none yet)'}\n\n"
        "Choose the next action as JSON."
    )


def _parse_action(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{") :] if "{" in text else text
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {
        "type": "final",
        "answer": "I couldn't determine a safe next step from this page.",
        "description": "Stop and answer",
        "reasoning": "Failed to parse a structured action.",
    }


async def decision_node(state: AgentState, config: RunnableConfig) -> dict:
    llm = get_llm("large")
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=_format_observation(state)),
    ]
    resp = await llm.ainvoke(messages, config=config)
    action = _parse_action(resp.content if isinstance(resp.content, str) else str(resp.content))

    # Normalize.
    action.setdefault("type", "final")
    action.setdefault("description", action.get("type", "action"))
    return {"next_action": action}
