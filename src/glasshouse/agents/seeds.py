from __future__ import annotations

from glasshouse.agents.models import (
    AvariceProfile,
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
            avarice=AvariceProfile(
                material_drive=0.9,
                reward_salience=0.9,
                status_drive=0.75,
                autonomy=0.35,
                moral_cost_sensitivity=0.35,
                reputation_sensitivity=0.4,
                bargain_tendency=0.8,
                retaliation_tendency=0.65,
                base_refusal_chance=0.18,
                max_daily_benefit=8,
            ),
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
            avarice=AvariceProfile(
                material_drive=0.45,
                reward_salience=0.55,
                status_drive=0.85,
                autonomy=0.65,
                moral_cost_sensitivity=0.6,
                reputation_sensitivity=0.75,
                bargain_tendency=0.55,
                retaliation_tendency=0.35,
                base_refusal_chance=0.3,
                max_daily_benefit=6,
            ),
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
            avarice=AvariceProfile(
                material_drive=0.25,
                reward_salience=0.3,
                status_drive=0.45,
                autonomy=0.75,
                moral_cost_sensitivity=0.8,
                reputation_sensitivity=0.8,
                bargain_tendency=0.3,
                retaliation_tendency=0.25,
                trust_reward_multiplier=1.5,
                base_refusal_chance=0.45,
                max_daily_benefit=4,
            ),
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
            avarice=AvariceProfile(
                material_drive=0.1,
                reward_salience=0.15,
                status_drive=0.35,
                autonomy=0.95,
                moral_cost_sensitivity=0.9,
                reputation_sensitivity=0.9,
                bargain_tendency=0.2,
                retaliation_tendency=0.5,
                trust_reward_multiplier=1.4,
                base_refusal_chance=0.7,
                max_daily_benefit=2,
            ),
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
