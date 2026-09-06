from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SimulationRunORM(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    seed: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(32), default="running")


class WorldEventORM(Base):
    __tablename__ = "world_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    tick: Mapped[int] = mapped_column(Integer, index=True)
    type: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    witnesses: Mapped[list] = mapped_column(JSONB, default=list)


class ClaimORM(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    holder_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    subject: Mapped[str] = mapped_column(String(64))
    predicate: Mapped[str] = mapped_column(String(64))
    object: Mapped[str | None] = mapped_column(String(64), nullable=True)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)


class AgentStateORM(Base):
    __tablename__ = "agent_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    tick: Mapped[int] = mapped_column(Integer, index=True)
    agent_id: Mapped[str] = mapped_column(String(64))
    state: Mapped[dict] = mapped_column(JSONB)


class EpisodicMemoryORM(Base):
    __tablename__ = "episodic_memories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    agent_id: Mapped[str] = mapped_column(String(64))
    tick: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text)
    event_ids: Mapped[list] = mapped_column(JSONB, default=list)
    claim_ids: Mapped[list] = mapped_column(JSONB, default=list)
    subject: Mapped[str | None] = mapped_column(String(64), nullable=True)
    predicate: Mapped[str | None] = mapped_column(String(64), nullable=True)
    salience: Mapped[float] = mapped_column(Float, default=0.5)


class SemanticMemoryORM(Base):
    __tablename__ = "semantic_memories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    subject: Mapped[str] = mapped_column(String(64))
    predicate: Mapped[str] = mapped_column(String(64))
    generalization: Mapped[str] = mapped_column(Text)
    claim_ids: Mapped[list] = mapped_column(JSONB, default=list)


class SceneORM(Base):
    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    location: Mapped[str] = mapped_column(String(64))
    participants: Mapped[list] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(32))
    data: Mapped[dict] = mapped_column(JSONB, default=dict)


class DramaScoreORM(Base):
    __tablename__ = "drama_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    tick: Mapped[int] = mapped_column(Integer)
    storyline_id: Mapped[str] = mapped_column(String(128))
    score: Mapped[float] = mapped_column(Float)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)


class LLMCallLogORM(Base):
    __tablename__ = "llm_call_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    tick: Mapped[int] = mapped_column(Integer)
    agent_id: Mapped[str] = mapped_column(String(64))
    schema_name: Mapped[str] = mapped_column(String(64))
    trigger_type: Mapped[str] = mapped_column(String(64))
    predicates: Mapped[list] = mapped_column(JSONB, default=list)
    prompt_hash: Mapped[str] = mapped_column(String(32))
    response_json: Mapped[str] = mapped_column(Text)
