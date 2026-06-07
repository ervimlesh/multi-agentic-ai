"""Event envelope for streaming graph progress to the React widget over SSE.

Each event is `{"type": <EventType>, ...payload}` serialized as JSON. The
frontend switches on `type` to render tokens, status chips, action cards, the
approval (Continue/Cancel) card, and the final answer.
"""
from __future__ import annotations

import json
from enum import Enum
from typing import Any


class EventType(str, Enum):
    RUN_STARTED = "run_started"
    NODE_STARTED = "node_started"      # a graph node began (e.g. "supervisor")
    STATUS = "status"                  # human-readable progress line
    TOKEN = "token"                    # streamed LLM token (final answer)
    APPROVAL_REQUIRED = "approval_required"  # Flow B: pause for Continue/Cancel
    FINAL = "final"                    # final_answer ready
    ERROR = "error"
    RUN_ENDED = "run_ended"


def event(type_: EventType, **payload: Any) -> dict[str, Any]:
    return {"type": type_.value, **payload}


def sse(data: dict[str, Any]) -> str:
    """Format a dict as an SSE `data:` frame."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
