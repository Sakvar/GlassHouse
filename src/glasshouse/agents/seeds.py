from __future__ import annotations

from glasshouse.agents.models import (
    Goals,
    Personality,
    SecretFact,
    SocialBoundaries,
)
from glasshouse.agents.state import AgentState
from glasshouse.relationships.models import RelationshipVector
from glasshouse.world.models import Activity, AgentRef


def create_seed_agents() -> dict[str, AgentState]:
    agents = {
        "max": AgentState(
            id="max",
            name="Max",
            secrets=(SecretFact(id="max_unpaid_debt", other_character_id="dan"),),
            personality=Personality(extraversion=0.8, competitiveness=0.9, impulsivity=0.7),
            goals=Goals(
                today="Spend time with Eva",
                secret="Wants to win at any cost; borrowed money from Dan, never repaid",
            ),
            ref=AgentRef(agent_id="max", location_id="bedroom_a", activity=Activity.IDLE),
            relationships={
                "eva": RelationshipVector(attraction=76),
                "dan": RelationshipVector(trust=60),
            },
        ),
        "eva": AgentState(
            id="eva",
            name="Eva",
            personality=Personality(extraversion=0.85, trustfulness=0.6),
            goals=Goals(
                today="Socialize",
                secret="Wants one person to trust",
            ),
            ref=AgentRef(agent_id="eva", location_id="living_room", activity=Activity.IDLE),
            relationships={
                "dan": RelationshipVector(affinity=-10),
                "max": RelationshipVector(attraction=40),
            },
        ),
        "dan": AgentState(
            id="dan",
            name="Dan",
            personality=Personality(extraversion=0.7, jealousy=0.85, trustfulness=0.75),
            goals=Goals(today="Hang out with friends", secret="Very jealous"),
            ref=AgentRef(agent_id="dan", location_id="bedroom_a", activity=Activity.IDLE),
            relationships={
                "eva": RelationshipVector(attraction=82),
                "max": RelationshipVector(trust=73),
            },
        ),
        "lea": AgentState(
            id="lea",
            name="Lea",
            personality=Personality(extraversion=0.5, impulsivity=0.4, trustfulness=0.55),
            goals=Goals(
                today="Observe the house",
                secret="Knows Max broke a promise about borrowed money",
            ),
            ref=AgentRef(
                agent_id="lea",
                location_id="living_room",
                activity=Activity.IDLE,
                attention=0.85,
            ),
            relationships={
                "max": RelationshipVector(trust=40, resentment=20),
            },
        ),
    }
    for aid, partners in {"max": ("eva",), "eva": ("max",), "dan": ("eva",), "lea": ()}.items():
        agents[aid].boundaries = SocialBoundaries(romantic_partners=partners)
    return agents


def sync_agent_refs(world_agents: dict[str, AgentRef], agent_states: dict[str, AgentState]) -> None:
    for agent_id, state in agent_states.items():
        if agent_id in world_agents:
            state.ref = world_agents[agent_id]
