"""Supervisor node.

Understands the task and picks the execution mode:
  - "vision":  one or more images attached -> analyze them (Groq vision).
  - "browser": URL + an action verb (buy/click/submit/login) -> drive the site.
  - "analyze": URL, no action -> fetch the page and answer from it (Flow A).
  - "chat":    no URL -> general conversation / Q&A.

Deterministic: image check + URL regex + action-verb check. No LLM call here, so
it's fast and free. Swap in an LLM intent classifier later if the heuristics
prove too blunt.
"""
from __future__ import annotations

import re

from app.graph.graph_state import AgentState

_URL_RE = re.compile(r"https?://[^\s<>\"')]+", re.IGNORECASE)

# Verbs that imply acting on a site rather than just reading it.
_ACTION_VERBS = (
    "buy",
    "purchase",
    "order",
    "checkout",
    "add to cart",
    "book",
    "subscribe",
    "log in",
    "login",
    "sign in",
    "submit",
    "fill",
    "click",
    "apply",
    "pay",
)


def _first_url(text: str) -> str | None:
    match = _URL_RE.search(text or "")
    return match.group(0).rstrip(".,);") if match else None


def _wants_action(text: str) -> bool:
    low = (text or "").lower()
    return any(verb in low for verb in _ACTION_VERBS)


def supervisor_node(state: AgentState) -> dict:
    task = state.get("task", "")
    url = _first_url(task)

    if state.get("images"):
        mode = "vision"
    elif url and _wants_action(task):
        mode = "browser"
    elif url:
        mode = "analyze"
    else:
        mode = "chat"

    return {"url": url, "mode": mode}
