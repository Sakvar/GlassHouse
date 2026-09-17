from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.state import get_engine

router = APIRouter()


@router.get("/{agent_id}")
def get_agent(agent_id: str) -> dict:
    engine = get_engine()
    agent = engine.agents.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")
    return agent.model_dump()


@router.get("/{agent_id}/relationships")
def get_relationships(agent_id: str) -> dict:
    engine = get_engine()
    agent = engine.agents.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")
    return {k: v.model_dump() for k, v in agent.relationships.items()}


@router.get("/{agent_id}/claims")
def get_claims(agent_id: str) -> list:
    engine = get_engine()
    agent = engine.agents.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")
    return [c.model_dump() for c in agent.claims.entries.values()]


@router.get("/{agent_id}/beliefs")
def get_beliefs(agent_id: str) -> list:
    engine = get_engine()
    agent = engine.agents.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")
    return [b.model_dump() for b in agent.beliefs.entries.values()]
