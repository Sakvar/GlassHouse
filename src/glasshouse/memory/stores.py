from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta

from pydantic import BaseModel, Field


class WorkingMemoryItem(BaseModel):
    tick: int
    sim_time: str
    content: str
    subject: str | None = None
    predicate: str | None = None
    salience: float = 0.5
    event_id: str | None = None
    claim_id: str | None = None


class EpisodicMemory(BaseModel):
    id: str
    tick: int
    summary: str
    event_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    subject: str | None = None
    predicate: str | None = None
    salience: float = 0.5


class SemanticMemory(BaseModel):
    id: str
    subject: str
    predicate: str
    generalization: str
    claim_ids: list[str] = Field(default_factory=list)
    embedding: list[float] | None = None


class MemoryStore(BaseModel):
    working: deque[WorkingMemoryItem] = Field(default_factory=deque)
    episodic: list[EpisodicMemory] = Field(default_factory=list)
    semantic: list[SemanticMemory] = Field(default_factory=list)

    def add_working(self, item: WorkingMemoryItem, sim_time: str, ttl_minutes: int = 5) -> None:
        self.working.append(item)
        cutoff = datetime.fromisoformat(sim_time) - timedelta(minutes=ttl_minutes)
        while self.working:
            head_time = datetime.fromisoformat(self.working[0].sim_time)
            if head_time < cutoff:
                self.working.popleft()
            else:
                break

    def add_episodic(self, memory: EpisodicMemory) -> None:
        self.episodic.append(memory)
