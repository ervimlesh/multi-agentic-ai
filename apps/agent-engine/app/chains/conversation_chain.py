"""General conversation + vision answering (chat mode and vision mode).

Handles the "just talk to me" path: a normal question (optionally with prior
conversation history) and optionally one or more attached images/screenshots.
When images are present it uses the Groq vision model; otherwise the large text
model. Streams tokens so the UI renders progressively.
"""
from __future__ import annotations

from typing import Any, AsyncIterator, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from app.llms.providers.groq_provider import get_llm

SYSTEM_PROMPT = (
    "You are a helpful, knowledgeable assistant. Answer the user's questions "
    "accurately and directly. Use Markdown for structure (headings, bold, lists, "
    "code blocks) when it helps readability. If you are unsure or a question is "
    "outside your knowledge, say so honestly rather than inventing facts. When an "
    "image is provided, describe and reason about what you actually see in it."
)


def _history_to_messages(history: list[dict] | None) -> list:
    out: list = []
    for turn in history or []:
        role = turn.get("role")
        content = turn.get("content", "")
        if not content:
            continue
        out.append(AIMessage(content=content) if role == "assistant" else HumanMessage(content=content))
    return out


def _user_message(task: str, images: list[str] | None) -> HumanMessage:
    if not images:
        return HumanMessage(content=task)
    # Multimodal content block for the vision model.
    parts: list[dict[str, Any]] = [{"type": "text", "text": task or "Describe this image."}]
    for url in images:
        parts.append({"type": "image_url", "image_url": {"url": url}})
    return HumanMessage(content=parts)


async def stream_reply(
    task: str,
    *,
    history: list[dict] | None = None,
    images: list[str] | None = None,
    config: Optional[RunnableConfig] = None,
) -> AsyncIterator[str]:
    """Stream an assistant reply (text or vision) token by token."""
    llm = get_llm("vision" if images else "large")
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *_history_to_messages(history),
        _user_message(task, images),
    ]
    async for chunk in llm.astream(messages, config=config):
        if chunk.content:
            yield chunk.content
