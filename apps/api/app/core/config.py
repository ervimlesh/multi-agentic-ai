"""Application configuration loaded from environment variables / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App ---
    PROJECT_NAME: str = "Multi-Agent AI Platform"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    # --- Database (SQLite by default so it runs with zero external services) ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"

    # --- JWT ---
    JWT_SECRET_KEY: str = "CHANGE-ME-super-secret-key-for-dev-only"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Password hashing ---
    BCRYPT_ROUNDS: int = 12

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
