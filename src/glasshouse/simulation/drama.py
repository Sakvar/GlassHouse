from __future__ import annotations

from pydantic import BaseModel, Field

from glasshouse.agents.state import AgentState
from glasshouse.cognition.claims import Claim, claim_chain
from glasshouse.world.models import WorldState


class DramaScore(BaseModel):
    storyline_id: str
    agents: list[str] = Field(default_factory=list)
    score: float = Field(ge=0.0, le=1.0)
    factors: list[str] = Field(default_factory=list)
    status: str = "latent"


def score_drama(
    agents: dict[str, AgentState],
    world: WorldState,
) -> list[DramaScore]:
    scores: list[DramaScore] = []

    triangle = _detect_love_triangle(agents)
    if triangle:
        scores.append(triangle)

    gossip = _detect_gossip_chains(agents)
    scores.extend(gossip)

    secrets = _detect_unshared_secrets(agents)
    scores.extend(secrets)

    return scores


def _detect_love_triangle(agents: dict[str, AgentState]) -> DramaScore | None:
    dan = agents.get("dan")
    max_a = agents.get("max")
    eva = agents.get("eva")
    if not all([dan, max_a, eva]):
        return None

    dan_eva = dan.get_relationship("eva").attraction
    max_eva = max_a.get_relationship("eva").attraction
    if dan_eva > 70 and max_eva > 70:
        return DramaScore(
            storyline_id="triangle_dan_eva_max",
            agents=["dan", "eva", "max"],
            score=0.87,
            factors=["rivalry", "unshared_attraction"],
            status="active",
        )
    return None


def _detect_gossip_chains(agents: dict[str, AgentState]) -> list[DramaScore]:
    scores: list[DramaScore] = []
    all_claims: dict[str, Claim] = {}
    for agent in agents.values():
        all_claims.update(agent.claims.entries)

    for claim_id, claim in all_claims.items():
        chain = claim_chain(all_claims, claim_id)
        if len(chain) >= 2:
            scores.append(
                DramaScore(
                    storyline_id=f"gossip_{claim_id[:8]}",
                    agents=[
                        c.holder_id or c.speaker_id or ""
                        for c in chain
                        if c.holder_id or c.speaker_id
                    ],
                    score=min(1.0, 0.5 + len(chain) * 0.15),
                    factors=["gossip_chain"],
                    status="active",
                )
            )
    return scores


def _detect_unshared_secrets(agents: dict[str, AgentState]) -> list[DramaScore]:
    scores: list[DramaScore] = []
    for agent_id, agent in agents.items():
        if agent.goals.secret:
            holders = [agent_id]
            for other_id, other in agents.items():
                if other_id == agent_id:
                    continue
                for claim in other.claims.entries.values():
                    if claim.subject == agent_id and claim.predicate.value.endswith("unrepaid"):
                        holders.append(other_id)
            if len(holders) == 1:
                scores.append(
                    DramaScore(
                        storyline_id=f"secret_{agent_id}",
                        agents=[agent_id],
                        score=0.6,
                        factors=["unshared_secret"],
                        status="latent",
                    )
                )
    return scores
