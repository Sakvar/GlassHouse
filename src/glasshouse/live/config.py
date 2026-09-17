from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


def database_url(value: str) -> str:
    if value.startswith(("postgres://", "postgresql://", "postgresql+asyncpg://")):
        return "postgresql+psycopg://" + value.split("://", 1)[1]
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./glasshouse.db"
    session_secret: str = "development-only-change-before-production"
    app_env: str = "development"
    tick_seconds: int = 120
    poll_seconds: int = 5
    season_locale: str = "ru"
    llm_enabled: bool = False
    api_key: str = field(default="", repr=False)
    narrator_model: str = ""
    narrator_fallbacks: tuple[str, ...] = ()
    site_url: str = ""
    app_name: str = "GlassHouse Live"
    llm_max_calls: int = 1
    llm_max_tokens: int = 600
    llm_input_chars: int = 12000
    llm_timeout: float = 15

    def __post_init__(self):
        if self.app_env not in ("development", "test", "production"):
            raise ValueError("Invalid APP_ENV")
        if self.app_env == "production" and (
            len(self.session_secret) < 32 or self.session_secret.startswith("development-")
        ):
            raise ValueError(
                "Production requires a random SESSION_SECRET of at least 32 characters"
            )
        if self.tick_seconds < 5 or self.poll_seconds < 1:
            raise ValueError("Invalid worker interval")
        if self.season_locale not in ("ru", "en"):
            raise ValueError("Invalid SEASON_LOCALE")
        if not 0 <= self.llm_max_calls <= 1 or not 64 <= self.llm_max_tokens <= 2000:
            raise ValueError("Invalid LLM budget")
        if not 1000 <= self.llm_input_chars <= 16000 or not 1 <= self.llm_timeout <= 60:
            raise ValueError("Invalid LLM input budget or timeout")

    @classmethod
    def from_env(cls):
        load_dotenv()
        return cls(
            database_url=database_url(os.getenv("DATABASE_URL") or "sqlite:///./glasshouse.db"),
            session_secret=os.getenv("SESSION_SECRET") or cls.session_secret,
            app_env=os.getenv("APP_ENV", "development"),
            tick_seconds=int(os.getenv("TICK_INTERVAL_SECONDS", "120")),
            poll_seconds=int(os.getenv("WORKER_POLL_SECONDS", "5")),
            season_locale=os.getenv("SEASON_LOCALE", "ru"),
            llm_enabled=os.getenv("LLM_ENABLED", "false").lower() == "true",
            api_key=os.getenv("OPENROUTER_API_KEY", ""),
            narrator_model=os.getenv("OPENROUTER_MODEL_NARRATOR", ""),
            narrator_fallbacks=tuple(
                x.strip()
                for x in os.getenv("OPENROUTER_MODEL_NARRATOR_FALLBACKS", "").split(",")
                if x.strip()
            ),
            site_url=os.getenv("OPENROUTER_SITE_URL", ""),
            app_name=os.getenv("OPENROUTER_APP_NAME", "GlassHouse Live"),
            llm_max_calls=int(os.getenv("LLM_MAX_CALLS_PER_TICK", "1")),
            llm_max_tokens=int(os.getenv("LLM_MAX_OUTPUT_TOKENS_PER_TICK", "600")),
            llm_input_chars=int(os.getenv("LLM_MAX_INPUT_CHARS", "12000")),
            llm_timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "15")),
        )
