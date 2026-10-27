from glasshouse.agents.seeds import create_seed_agents
from glasshouse.show.models import OfferActionType, OfferStatus, ViewerOffer
from glasshouse.show.offers import evaluate_offer, price_offer


def make_offer(actor_id="max", points=3, action=OfferActionType.START_CONVERSATION):
    return ViewerOffer(
        id="offer-1",
        viewer_id="viewer-key",
        story_goal_id="goal:1:conversation",
        tick=1,
        actor_id=actor_id,
        target_id="eva",
        action_type=action,
        world_points=points,
    )


def test_price_increases_with_risk_fatigue_and_accumulated_benefit():
    max_agent = create_seed_agents()["max"]
    low = price_offer(max_agent, OfferActionType.START_CONVERSATION, "eva").minimum
    risky = price_offer(max_agent, OfferActionType.PUBLIC_STATEMENT, "eva").minimum
    max_agent.current.fatigue = 1
    max_agent.avarice.accumulated_benefit = max_agent.avarice.max_daily_benefit
    expensive = price_offer(max_agent, OfferActionType.PUBLIC_STATEMENT, "eva").minimum
    assert low <= risky < expensive


def test_hard_refusal_cannot_be_bought_and_daily_cap_is_absolute():
    actor = create_seed_agents()["max"]
    offer = make_offer(points=3)
    blocked = evaluate_offer(
        actor=actor,
        offers=(offer,),
        seed=42,
        tick=1,
        hard_refusal="personal_boundary",
    )
    assert blocked.status == OfferStatus.REFUSED
    assert blocked.reason == "personal_boundary"

    actor.avarice.accumulated_benefit = actor.avarice.max_daily_benefit
    capped = evaluate_offer(actor=actor, offers=(offer,), seed=42, tick=1)
    assert capped.status == OfferStatus.REFUSED
    assert capped.reason == "daily_benefit_limit"


def test_offer_decision_is_deterministic():
    actor = create_seed_agents()["max"]
    offer = make_offer()
    first = evaluate_offer(actor=actor, offers=(offer,), seed=19, tick=1)
    second = evaluate_offer(actor=actor, offers=(offer,), seed=19, tick=1)
    assert first == second
