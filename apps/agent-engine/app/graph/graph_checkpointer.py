"""Checkpointer factory.

The spine (Flow A) is stateless per request, so an in-memory saver is fine.
Flow B's human-in-the-loop pause/resume needs a durable store — switch
CHECKPOINTER=postgres (see .env.example) once that phase lands.
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver

from app.config.settings import settings


def get_checkpointer():
    if settings.CHECKPOINTER == "postgres":
        # Phase 3: from langgraph.checkpoint.postgres import PostgresSaver
        # return PostgresSaver.from_conn_string(settings.POSTGRES_DSN)
        raise NotImplementedError(
            "Postgres checkpointer arrives with Flow B (HITL). "
            "Set CHECKPOINTER=memory for the spine."
        )
    return MemorySaver()
