from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.state import get_engine
from glasshouse.cognition.claims import claim_chain

router = APIRouter()


@router.get("/{claim_id}/provenance")
def get_claim_provenance(claim_id: str) -> list:
    engine = get_engine()
    all_claims = {}
    for agent in engine.agents.values():
        all_claims.update(agent.claims.entries)

    if claim_id not in all_claims:
        raise HTTPException(404, f"Claim {claim_id} not found")

    chain = claim_chain(all_claims, claim_id)
    return [c.model_dump() for c in chain]
