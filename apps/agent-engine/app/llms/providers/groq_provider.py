"""Groq LLM provider.

Two tiers so cheap nodes (intent/safety classification, page cleanup) don't pay
70B prices while reasoning nodes (supervisor, planner, decision, synthesis) do.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from langchain_groq import ChatGroq

from app.config.settings import settings

Tier = Literal["large", "fast", "vision"]

_MODELS = {
    "large": lambda: settings.GROQ_MODEL_LARGE,
    "fast": lambda: settings.GROQ_MODEL_FAST,
    "vision": lambda: settings.GROQ_MODEL_VISION,
}


@lru_cache(maxsize=8)
def get_llm(tier: Tier = "large", temperature: float | None = None) -> ChatGroq:
    """Return a cached ChatGroq client for the given tier.

    Cached per (tier, temperature) so we reuse one client instead of opening a
    new HTTP pool on every node call.
    """
    if not settings.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your key."
        )

    model = _MODELS.get(tier, _MODELS["large"])()
    return ChatGroq(
        model=model,
        api_key=settings.GROQ_API_KEY,
        temperature=settings.LLM_TEMPERATURE if temperature is None else temperature,
        max_tokens=settings.LLM_MAX_TOKENS,
    )
