"""Responder node — general chat and image/vision answering.

Used for the "chat" and "vision" modes (no URL to fetch, no site to drive). It
streams a reply from the conversation chain, threading prior turns (history) for
multi-turn memory and any attached images for vision.
"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from app.chains.conversation_chain import stream_reply
from app.graph.graph_state import AgentState


async def respond_node(state: AgentState, config: RunnableConfig) -> dict:
    parts: list[str] = []
    async for token in stream_reply(
        state.get("task", ""),
        history=state.get("history"),
        images=state.get("images"),
        config=config,
    ):
        parts.append(token)
    return {"final_answer": "".join(parts)}
