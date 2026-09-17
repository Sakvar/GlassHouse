from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now() -> datetime:
    # Store UTC without timezone consistently on PostgreSQL and SQLite.
    from datetime import UTC
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    display_name: Mapped[str] = mapped_column(String(40))
    locale: Mapped[str] = mapped_column(String(2), default='ru')
    created_at: Mapped[datetime] = mapped_column(default=now)
    __table_args__ = (CheckConstraint("locale IN ('ru', 'en')"),)


class Season(Base):
    __tablename__ = 'seasons'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(20), default='active')
    config: Mapped[dict] = mapped_column(JSON)
    snapshot: Mapped[dict] = mapped_column(JSON)
    revision: Mapped[int] = mapped_column(default=0)
    next_tick_at: Mapped[datetime] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(default=now)
    updated_at: Mapped[datetime] = mapped_column(default=now)


class ShowEventRow(Base):
    __tablename__ = 'show_events'
    season_id: Mapped[str] = mapped_column(ForeignKey('seasons.id'), primary_key=True)
    sequence: Mapped[int] = mapped_column(primary_key=True)
    revision: Mapped[int]
    tick: Mapped[int]
    kind: Mapped[str] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=now)


class VoteRow(Base):
    __tablename__ = 'viewer_votes'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    season_id: Mapped[str] = mapped_column(ForeignKey('seasons.id'))
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    tick: Mapped[int]
    goal_id: Mapped[str] = mapped_column(String(200))
    points: Mapped[int]
    request_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(default=now)
    __table_args__ = (
        CheckConstraint('points >= 1 AND points <= 3'),
        UniqueConstraint('season_id', 'user_id', 'request_id'),
        Index('ix_votes_user_tick', 'season_id', 'user_id', 'tick'),
    )


class Budget(Base):
    __tablename__ = 'viewer_budgets'
    season_id: Mapped[str] = mapped_column(ForeignKey('seasons.id'), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), primary_key=True)
    tick: Mapped[int] = mapped_column(primary_key=True)
    spent: Mapped[int] = mapped_column(default=0)
    __table_args__ = (CheckConstraint('spent >= 0 AND spent <= 3'),)


class RecapRow(Base):
    __tablename__ = 'public_recaps'
    season_id: Mapped[str] = mapped_column(ForeignKey('seasons.id'), primary_key=True)
    tick: Mapped[int] = mapped_column(primary_key=True)
    translations: Mapped[dict] = mapped_column(JSON)


class LLMRun(Base):
    __tablename__ = 'llm_runs'
    season_id: Mapped[str] = mapped_column(ForeignKey('seasons.id'), primary_key=True)
    tick: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(32), default='narrator')
    model_requested: Mapped[str] = mapped_column(String(200))
    model_used: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32))
    prompt_tokens: Mapped[int | None]
    completion_tokens: Mapped[int | None]
    cost: Mapped[float | None]
    latency_ms: Mapped[int]
    error_type: Mapped[str | None] = mapped_column(String(100))


class AuthSession(Base):
    __tablename__ = 'auth_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    expires_at: Mapped[datetime] = mapped_column(index=True)


class RateLimit(Base):
    __tablename__ = 'rate_limits'
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window: Mapped[int]
    attempts: Mapped[int]
