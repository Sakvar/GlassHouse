from __future__ import annotations

from typing import TYPE_CHECKING

from glasshouse.cognition.claims import ClaimPredicate
from glasshouse.memory.stores import EpisodicMemory, WorkingMemoryItem

if TYPE_CHECKING:
    from glasshouse.agents.state import AgentState


def retrieve_relevant(
    agent: AgentState,
    subject: str | None = None,
    predicate: ClaimPredicate | None = None,
    location: str | None = None,
    limit: int = 10,
) -> list[WorkingMemoryItem | EpisodicMemory]:
    results: list[tuple[float, WorkingMemoryItem | EpisodicMemory]] = []

    for item in agent.memory.working:
        score = _score(item, subject, predicate, location)
        if score > 0:
            results.append((score, item))

    for item in agent.memory.episodic:
        score = _score(item, subject, predicate, location)
        if score > 0:
            results.append((score, item))

    for claim in agent.claims.entries.values():
        if predicate and claim.predicate == predicate:
            results.append((0.8, WorkingMemoryItem(
                tick=0,
                sim_time="",
                content=f"claim:{claim.predicate.value}",
                subject=claim.subject,
                predicate=claim.predicate.value,
                claim_id=claim.id,
            )))

    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:limit]]


def _score(
    item: WorkingMemoryItem | EpisodicMemory,
    subject: str | None,
    predicate: ClaimPredicate | None,
    location: str | None,
) -> float:
    score = getattr(item, "salience", 0.5)
    item_subject = getattr(item, "subject", None)
    item_predicate = getattr(item, "predicate", None)
    if subject and item_subject == subject:
        score += 0.4
    if predicate and item_predicate == predicate.value:
        score += 0.4
    return score
