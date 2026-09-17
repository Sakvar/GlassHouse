from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from glasshouse.world.models import WorldEvent, WorldState
from glasshouse.world.perception import PerceptionLevel, compute_perception


class SensoryContent(BaseModel):
    event_type: str
    actor: str | None = None
    claim_id: str | None = None
    snippet: str = ""
    detail_level: str = "full"


class KnowledgeEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_id: str
    agent_id: str
    perception_level: PerceptionLevel
    tick: int
    location: str
    sensory_content: SensoryContent


class KnowledgeStore(BaseModel):
    entries: dict[str, KnowledgeEntry] = Field(default_factory=dict)

    def add(self, entry: KnowledgeEntry) -> KnowledgeEntry:
        self.entries[entry.id] = entry
        return entry

    def get(self, entry_id: str) -> KnowledgeEntry | None:
        return self.entries.get(entry_id)

    def by_event(self, event_id: str) -> list[KnowledgeEntry]:
        return [e for e in self.entries.values() if e.event_id == event_id]

    def by_agent(self, agent_id: str) -> list[KnowledgeEntry]:
        return [e for e in self.entries.values() if e.agent_id == agent_id]


def _build_sensory_content(event: WorldEvent, level: PerceptionLevel) -> SensoryContent:
    claim_id = event.payload.get("claim_id")
    exact_text = event.payload.get("exact_text", "")
    if level == PerceptionLevel.FULL:
        snippet = exact_text or f"{event.type.value} by {event.actor}"
        detail = "full"
    elif level == PerceptionLevel.PARTIAL:
        snippet = exact_text[: max(20, len(exact_text) // 2)] if exact_text else "muffled sounds"
        detail = "partial"
    else:
        snippet = ""
        detail = "none"

    return SensoryContent(
        event_type=event.type.value,
        actor=event.actor,
        claim_id=claim_id,
        snippet=snippet,
        detail_level=detail,
    )


def perceive_event(world: WorldState, event: WorldEvent) -> list[KnowledgeEntry]:
    entries: list[KnowledgeEntry] = []
    for agent_id, agent_ref in world.agents.items():
        if agent_id == event.actor and event.type.value == "utterance":
            continue
        level = compute_perception(event, agent_ref, event.location)
        if level == PerceptionLevel.NONE:
            continue
        sensory = _build_sensory_content(event, level)
        entries.append(
            KnowledgeEntry(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{event.id}:{agent_id}:{world.tick}")),
                event_id=event.id,
                agent_id=agent_id,
                perception_level=level,
                tick=world.tick,
                location=agent_ref.location_id,
                sensory_content=sensory,
            )
        )
    return entries


def write_knowledge(agent_knowledge: KnowledgeStore, entry: KnowledgeEntry) -> KnowledgeEntry:
    return agent_knowledge.add(entry)
