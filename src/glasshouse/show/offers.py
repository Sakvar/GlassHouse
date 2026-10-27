from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from glasshouse.agents.state import AgentState
from glasshouse.show.models import (
    OfferActionType,
    OfferDecision,
    OfferStatus,
    ViewerOffer,
)

BASE_PRICES: dict[OfferActionType, int] = {
    OfferActionType.START_CONVERSATION: 1,
    OfferActionType.HOUSEHOLD_TASK: 2,
    OfferActionType.SPEND_TIME: 3,
    OfferActionType.DEESCALATE: 3,
    OfferActionType.PUBLIC_STATEMENT: 5,
    OfferActionType.SHARE_KNOWN_FACT: 7,
}

RISK: dict[OfferActionType, float] = {
    OfferActionType.START_CONVERSATION: 0.1,
    OfferActionType.HOUSEHOLD_TASK: 0.15,
    OfferActionType.SPEND_TIME: 0.35,
    OfferActionType.DEESCALATE: 0.4,
    OfferActionType.PUBLIC_STATEMENT: 0.75,
    OfferActionType.SHARE_KNOWN_FACT: 0.9,
}

PUBLIC_ACTIONS = {OfferActionType.PUBLIC_STATEMENT, OfferActionType.SHARE_KNOWN_FACT}


@dataclass(frozen=True)
class PriceQuote:
    minimum: int
    maximum: int
    risk: float


def price_offer(
    actor: AgentState,
    action_type: OfferActionType,
    target_id: str | None,
    source_key: str = "audience",
) -> PriceQuote:
    profile = actor.avarice
    relation = actor.get_relationship(target_id) if target_id else None
    viewer = actor.viewer_relations.get(source_key)
    risk = RISK[action_type]
    public = action_type in PUBLIC_ACTIONS
    fatigue = actor.current.fatigue
    trust = ((relation.trust + 100) / 200) if relation else 0.5
    source_trust = ((viewer.trust + 100) / 200) if viewer else 0.5

    multiplier = 1.0
    multiplier += risk * (0.8 * profile.moral_cost_sensitivity)
    multiplier += (0.5 if public else 0.0) * profile.reputation_sensitivity
    multiplier += fatigue * 0.75
    multiplier += profile.autonomy * 0.45
    multiplier += profile.accumulated_benefit / max(1, profile.max_daily_benefit) * 0.8
    multiplier += profile.broken_promise_count * 0.1
    multiplier -= profile.material_drive * 0.45
    multiplier -= profile.reward_salience * 0.25
    multiplier -= trust * 0.25
    multiplier -= source_trust * 0.15 * profile.trust_reward_multiplier
    remembered = profile.price_memory.get(action_type.value, 0)
    minimum = max(1, math.ceil(BASE_PRICES[action_type] * max(0.5, multiplier)))
    minimum = max(minimum, remembered)
    return PriceQuote(minimum=minimum, maximum=minimum + 2, risk=risk)


def _roll(seed: int, tick: int, actor_id: str, offer_ids: tuple[str, ...]) -> float:
    material = f"{seed}:{tick}:{actor_id}:{':'.join(offer_ids)}".encode()
    return int(hashlib.sha256(material).hexdigest()[:12], 16) / float(0xFFFFFFFFFFFF)


def evaluate_offer(
    *,
    actor: AgentState,
    offers: tuple[ViewerOffer, ...],
    seed: int,
    tick: int,
    hard_refusal: str | None = None,
) -> OfferDecision:
    first = offers[0]
    offered = sum(item.world_points for item in offers)
    quote = price_offer(actor, first.action_type, first.target_id, first.viewer_id)
    common = dict(
        offer_ids=tuple(item.id for item in offers),
        action_type=first.action_type,
        actor_id=first.actor_id,
        target_id=first.target_id,
        offered_points=offered,
        quoted_price=quote.minimum,
    )
    if hard_refusal:
        return OfferDecision(**common, status=OfferStatus.REFUSED, reason=hard_refusal)
    if actor.avarice.accumulated_benefit >= actor.avarice.max_daily_benefit:
        return OfferDecision(**common, status=OfferStatus.REFUSED, reason="daily_benefit_limit")

    refusal = actor.avarice.base_refusal_chance
    refusal += quote.risk * actor.avarice.moral_cost_sensitivity * 0.25
    refusal += actor.avarice.autonomy * 0.15
    refusal -= actor.avarice.material_drive * min(0.25, offered / 40)
    if offered >= quote.minimum and _roll(seed, tick, actor.id, common["offer_ids"]) >= refusal:
        return OfferDecision(**common, status=OfferStatus.ACCEPTED, reason="price_met")
    if offered >= quote.minimum:
        return OfferDecision(**common, status=OfferStatus.REFUSED, reason="voluntary_refusal")
    if offered + 1 >= quote.minimum and actor.avarice.bargain_tendency >= 0.45:
        return OfferDecision(
            **common,
            status=OfferStatus.NEGOTIATING,
            reason="higher_price_required",
        )
    if offered * 2 >= quote.minimum and first.action_type in {
        OfferActionType.PUBLIC_STATEMENT,
        OfferActionType.SHARE_KNOWN_FACT,
        OfferActionType.SPEND_TIME,
    }:
        return OfferDecision(
            **common,
            status=OfferStatus.ALTERNATIVE,
            reason="safer_alternative",
            alternative=OfferActionType.START_CONVERSATION,
        )
    if offered * 3 >= quote.minimum * 2:
        return OfferDecision(**common, status=OfferStatus.PARTIAL, reason="partial_only")
    return OfferDecision(**common, status=OfferStatus.REFUSED, reason="price_not_met")
