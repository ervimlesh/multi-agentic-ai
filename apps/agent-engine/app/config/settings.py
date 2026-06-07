"""Runtime configuration for the agent-engine service.

Reads from environment / a local .env file. The only required value is
GROQ_API_KEY. Model ids default to current Groq production models — override
them via env if Groq rotates the names.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- service ---
    PROJECT_NAME: str = "agent-engine"
    HOST: str = "0.0.0.0"
    PORT: int = 8100
    CORS_ORIGINS: list[str] = ["*"]

    # --- Groq ---
    GROQ_API_KEY: str = ""
    # Big model: supervisor, planner, decision, reviewer, synthesis, chat.
    GROQ_MODEL_LARGE: str = "llama-3.3-70b-versatile"
    # Fast/cheap model: intent + safety classification, page cleanup.
    GROQ_MODEL_FAST: str = "llama-3.1-8b-instant"
    # Vision model for image/screenshot analysis (must accept image_url content).
    GROQ_MODEL_VISION: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 1024

    # --- Flow A: URL analyze ---
    FETCH_TIMEOUT_SECONDS: float = 20.0
    FETCH_MAX_CHARS: int = 16000  # truncate page text before sending to the LLM
    FETCH_USER_AGENT: str = (
        "Mozilla/5.0 (compatible; AgentEngine/0.1; +https://example.com/bot)"
    )

    # --- Flow B: browser automation (Playwright) ---
    BROWSER_HEADLESS: bool = True
    BROWSER_NAV_TIMEOUT_MS: int = 30000
    BROWSER_SETTLE_MS: int = 2000        # wait after navigation for SPA render
    BROWSER_MAX_STEPS: int = 6           # safety cap on the observe→act loop
    BROWSER_MAX_ELEMENTS: int = 40       # interactive elements shown to the LLM
    BROWSER_TEXT_LIMIT: int = 4000       # page text chars shown to the LLM
    BROWSER_USER_AGENT: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )

    # --- checkpointer (Postgres in phase 3; memory for the spine) ---
    CHECKPOINTER: str = "memory"  # "memory" | "postgres"
    POSTGRES_DSN: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
