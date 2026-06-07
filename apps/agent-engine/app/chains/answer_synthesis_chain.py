"""Analyze fetched page text and answer the user's task (Flow A).

Uses the large Groq model. Returns an async token stream so the API can pipe
tokens straight to the React widget over SSE.
"""
from __future__ import annotations

from typing import Any, AsyncIterator, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from app.llms.providers.groq_provider import get_llm

SYSTEM_PROMPT = (
    "You are a web page analyst. You are given the readable text of a single web "
    "page and a user request. Answer the request using ONLY the page content. "
    "If the page does not contain the answer, say so plainly. Be concise and "
    "factual; do not invent details that are not in the text."
)


def _build_messages(task: str, page: dict) -> list:
    page_block = (
        f"URL: {page.get('url')}\n"
        f"TITLE: {page.get('title')}\n"
        f"{'[NOTE: page text was truncated]' if page.get('truncated') else ''}\n"
        f"--- PAGE TEXT START ---\n{page.get('text')}\n--- PAGE TEXT END ---"
    )
    user_block = f"USER REQUEST:\n{task}\n\n{page_block}"
    return [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_block)]


async def stream_answer(
    task: str, page: dict, config: Optional[RunnableConfig] = None
) -> AsyncIterator[str]:
    """Yield answer tokens as they arrive from Groq.

    `config` must be forwarded from the graph node so LangGraph's callbacks reach
    the model — on Python 3.10 they are NOT auto-propagated through astream, so
    without this the UI gets no streamed tokens.
    """
    llm = get_llm("large")
    async for chunk in llm.astream(_build_messages(task, page), config=config):
        if chunk.content:
            yield chunk.content


async def synthesize_answer(
    task: str, page: dict, config: Optional[RunnableConfig] = None
) -> str:
    """Non-streaming variant (full string)."""
    llm = get_llm("large")
    resp = await llm.ainvoke(_build_messages(task, page), config=config)
    return resp.content
