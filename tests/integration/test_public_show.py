import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.api.main import app
from apps.api.state import get_engine, set_engine
from glasshouse.cognition.claims import Claim, ClaimPredicate
from glasshouse.relationships.models import RelationshipVector
from glasshouse.show.director import PublicShowDirector
from glasshouse.show.models import GoalStatus, StoryCategory, ViewerVote
from glasshouse.simulation.engine import SimulationEngine
from glasshouse.simulation.replay import replay_from
from glasshouse.simulation.snapshot import SimulationSnapshot
from glasshouse.world.models import Activity, WorldEvent, WorldEventType


def choose(engine, category, viewer="viewer-1", points=3):
    goal = next(g for g in engine.show.active_goals() if g.category == category)
    engine.show.vote(
        ViewerVote(viewer_id=viewer, story_goal_id=goal.id, tick=goal.tick, influence_points=points)
    )
    return goal


def resolved(engine):
    return next(
        g
        for g in engine.show.goals
        if g.tick == engine.world.tick and g.status == GoalStatus.RESOLVED
    )


def test_clean_start_and_configurable_clock():
    engine = SimulationEngine()
    start = datetime.fromisoformat(engine.world.sim_time)
    assert len(engine.show.active_goals()) == 5
    events = engine.tick()
    assert events and len(engine.show.recaps) == 1
    assert datetime.fromisoformat(engine.world.sim_time) == start + timedelta(hours=2)
    assert engine.llm is None
    assert engine.show.recaps[-1].event_ids == tuple(e.id for e in events)
    configured = SimulationEngine(tick_minutes=30)
    configured.run(hours=1)
    assert configured.world.tick == 2
    assert datetime.fromisoformat(configured.world.sim_time) == start + timedelta(hours=1)


def test_seed_and_votes_reproduce_full_history_and_nonzero_snapshot():
    engines = [SimulationEngine(seed=19) for _ in range(2)]
    for engine in engines:
        for _ in range(6):
            choose(engine, StoryCategory.CONVERSATION, points=2)
            engine.tick()
    assert engines[0].snapshot().model_dump_json() == engines[1].snapshot().model_dump_json()
    original = engines[0]
    choose(original, StoryCategory.CONFLICT)
    snapshot = SimulationSnapshot.model_validate_json(original.snapshot().model_dump_json())
    original.tick()
    replayed = replay_from(snapshot, [], ticks=1)
    assert original.snapshot().model_dump_json() == replayed.snapshot().model_dump_json()
    # Frozen audience history survives external JSON parsing and projection rebuilding.
    rebuilt = PublicShowDirector(replayed, replayed.show.journal)
    assert rebuilt.goals == replayed.show.goals
    assert rebuilt.recaps == replayed.show.recaps


def test_vote_wins_and_has_provenance_and_round_closes():
    engine = SimulationEngine()
    winner = choose(engine, StoryCategory.CONFLICT)
    choose(engine, StoryCategory.CONVERSATION, viewer="v2", points=2)
    old_journal = engine.show.journal
    engine.tick()
    assert resolved(engine).id == winner.id
    assert resolved(engine).result.outcome == "disagreement"
    assert engine.show.journal[: len(old_journal)] == old_journal
    selection = next(e for e in engine.show.journal if e.kind == "goal_selected")
    assert set(selection.cause_ids) == {e.id for e in old_journal if e.kind == "vote_cast"}
    assert len([g for g in engine.show.goals if g.status == GoalStatus.EXPIRED]) == 4
    assert all(g.tick == 2 for g in engine.show.active_goals())
    with pytest.raises(ValueError):
        engine.show.vote(ViewerVote(viewer_id="new", story_goal_id=winner.id, tick=1))


def test_seeded_tie_is_deterministic_and_not_director_score():
    winners = set()
    for seed in range(10):
        pair = [SimulationEngine(seed=seed), SimulationEngine(seed=seed)]
        for engine in pair:
            choose(engine, StoryCategory.CONFLICT, points=1)
            choose(engine, StoryCategory.CONVERSATION, viewer="v2", points=1)
            engine.tick()
            assert resolved(engine).category in (StoryCategory.CONFLICT, StoryCategory.CONVERSATION)
        assert resolved(pair[0]).id == resolved(pair[1]).id
        winners.add(resolved(pair[0]).category)
    assert len(winners) == 2


def test_limit_aggregates_across_goals_is_atomic_and_resets_each_tick():
    engine = SimulationEngine()
    choose(engine, StoryCategory.CONVERSATION, points=2)
    choose(engine, StoryCategory.CONFLICT, points=1)
    before = engine.snapshot().model_dump_json()
    with pytest.raises(ValueError):
        choose(engine, StoryCategory.RECONCILIATION, points=1)
    assert engine.snapshot().model_dump_json() == before
    engine.tick()
    goal = next(iter(engine.show.active_goals()))

    def cast(_):
        try:
            engine.show.vote(ViewerVote(viewer_id="viewer-1", story_goal_id=goal.id, tick=2))
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(cast, range(10))) == 3


@pytest.mark.parametrize("points", [0, -1, 1.5, True, "1"])
def test_vote_requires_positive_integer(points):
    with pytest.raises(ValidationError):
        ViewerVote(viewer_id="v", story_goal_id="goal", tick=1, influence_points=points)


@pytest.mark.parametrize(
    "restriction",
    [
        "incompatible",
        "romance_block",
        "blocked_person",
        "low_trust",
        "low_affinity",
        "low_attraction",
        "conversation_block",
        "sleeping",
    ],
)
@pytest.mark.parametrize("side", [0, 1])
def test_romance_requires_both_characters_consent(restriction, side):
    engine = SimulationEngine()
    goal = choose(engine, StoryCategory.ROMANCE_OPPORTUNITY)
    a, b = (engine.agents[x] for x in goal.eligible_characters)
    for person, other in ((a, b), (b, a)):
        person.boundaries.romantic_partners = (other.id,)
        person.relationships[other.id] = RelationshipVector(trust=80, affinity=80, attraction=80)
    person, other = ((a, b), (b, a))[side]
    if restriction == "incompatible":
        person.boundaries.romantic_partners = ()
    elif restriction == "romance_block":
        person.boundaries.romance_allowed = False
    elif restriction == "blocked_person":
        person.boundaries.blocked_characters = (other.id,)
    elif restriction.startswith("low_"):
        setattr(person.relationships[other.id], restriction.removeprefix("low_"), 0)
    elif restriction == "conversation_block":
        person.boundaries.private_conversation_allowed = False
    else:
        person.ref = person.ref.model_copy(update={"activity": Activity.SLEEPING})
        engine.world.agents[person.id] = person.ref
    engine.tick()
    result = resolved(engine).result
    assert result.outcome == "refusal"
    assert result.relationship_changes == ()  # No punishment for refusing.
    assert engine.show.timeline().items[-1].result == result
    assert engine.show.recaps[-1].why_it_matters


def test_mutual_romance_can_succeed():
    engine = SimulationEngine()
    goal = choose(engine, StoryCategory.ROMANCE_OPPORTUNITY)
    a, b = (engine.agents[x] for x in goal.eligible_characters)
    for person, other in ((a, b), (b, a)):
        person.boundaries.romantic_partners = (other.id,)
        person.relationships[other.id] = RelationshipVector(trust=40, affinity=30, attraction=60)
    engine.tick()
    assert resolved(engine).result.outcome == "date"
    assert resolved(engine).result.relationship_changes
    assert a.ref.location_id == b.ref.location_id


def test_secret_has_evidence_and_provenance_without_magical_knowledge():
    engine = SimulationEngine()
    choose(engine, StoryCategory.REVEAL_SECRET)
    engine.tick()
    result = resolved(engine).result
    assert result.revealed_secret_ids == ("max_unpaid_debt",)
    root = engine.agents["max"].claims.get("secret:max_unpaid_debt")
    assert root and root.evidence_ids
    received = next(iter(engine.agents["dan"].claims.entries.values()))
    assert received.provenance.source_claim_id == root.id
    assert received.evidence_ids
    for aid in ("eva", "lea"):
        assert not engine.agents[aid].claims.entries
    assert all(g.category != StoryCategory.REVEAL_SECRET for g in engine.show.active_goals())


def test_secret_disclosure_can_be_refused_and_no_fact_is_invented():
    engine = SimulationEngine()
    engine.agents["max"].boundaries.secret_sharing_allowed = False
    choose(engine, StoryCategory.REVEAL_SECRET)
    engine.tick()
    assert resolved(engine).result.outcome == "refusal"
    assert not engine.agents["max"].claims.entries
    agents = SimulationEngine().agents
    agents["max"].secrets = ()
    custom = SimulationEngine(agents=agents)
    assert all(g.category != StoryCategory.REVEAL_SECRET for g in custom.show.active_goals())


def test_llm_error_logs_context_and_fallback_keeps_ticking(caplog):
    class BrokenLLM:
        def generate_structured(self, *args, **kwargs):
            raise RuntimeError("provider unavailable")

    engine = SimulationEngine(llm=BrokenLLM())
    engine.emit_truth_admission(
        "max", Claim(subject="max", predicate=ClaimPredicate.BORROWED_MONEY_UNREPAID)
    )
    engine.tick()
    failures = [r.diagnostic for r in caplog.records if hasattr(r, "diagnostic")]
    assert failures and failures[0]["error_type"] == "RuntimeError"
    assert failures[0]["tick"] == 1 and failures[0]["schema"]
    assert failures[0]["fallback"] == "deterministic_director"
    assert engine.show.recaps and resolved(engine).result
    engine.tick()
    assert len(engine.show.recaps) == 2


def test_scene_summary_failure_uses_template_and_snapshot_preserves_scene(caplog):
    class BrokenLLM:
        def generate_structured(self, *args, **kwargs):
            raise RuntimeError("offline")

    engine = SimulationEngine(llm=BrokenLLM())
    scene = engine.scene_manager.start_scene("kitchen", ["max"], [], engine.world.sim_time)
    scene.idle_turns = 2
    # A refusal keeps this tick semantically idle, triggering scene collapse.
    choose(engine, StoryCategory.ROMANCE_OPPORTUNITY)
    snap = engine.snapshot()
    restored = replay_from(snap, [], ticks=0)
    assert restored.scene_manager.scenes == engine.scene_manager.scenes
    engine.tick()
    assert any(
        getattr(r, "diagnostic", {}).get("trigger") == "scene_collapse" for r in caplog.records
    )
    assert engine.agents["max"].memory.episodic[-1].summary == "Conversation at kitchen"


def test_snapshot_restores_pending_events():
    engine = SimulationEngine()
    event = WorldEvent(
        id="external", tick=1, type=WorldEventType.SIT, actor="max", location="bedroom_a"
    )
    engine.inject_event(event)
    snap = engine.snapshot()
    engine.tick()
    restored = replay_from(snap, [], ticks=1)
    assert engine.snapshot().model_dump_json() == restored.snapshot().model_dump_json()


def test_public_api_shared_state_validation_and_no_private_leaks():
    previous = get_engine()
    try:
        engine = SimulationEngine()
        set_engine(engine)
        with TestClient(app) as first, TestClient(app) as second:
            season = first.get("/public/season").json()
            assert season["voting_tick"] == 1 and season["tick_minutes"] == 120
            assert "secret" not in json.dumps(season).lower()
            goals = first.get("/public/goals").json()
            goal = next(g for g in goals if g["category"] == "conflict")
            vote = {
                "viewer_id": "alice",
                "story_goal_id": goal["id"],
                "tick": 1,
                "influence_points": 3,
            }
            assert first.post("/public/votes", json=vote).status_code == 201
            assert second.post("/public/votes", json=vote).status_code == 409
            assert (
                first.post("/public/votes", json={**vote, "influence_points": True}).status_code
                == 422
            )
            assert (
                first.post("/public/votes", json={**vote, "story_goal_id": "missing"}).status_code
                == 404
            )
            assert first.post("/public/dev/ticks", json={"ticks": 0}).status_code == 422
            assert first.post("/public/dev/ticks", json={"ticks": 101}).status_code == 422
            assert first.post("/public/dev/ticks", json={}).status_code == 200
            assert second.get("/public/season").json()["tick"] == 1
            timeline = second.get("/public/timeline").json()
            assert timeline["items"][0]["story_goal_id"] == goal["id"]
            assert len(timeline["recaps"]) == 1
            assert "viewer_id" not in json.dumps(timeline)
            assert second.post("/public/dev/ticks", json={"ticks": 2}).json()["tick"] == 3
            assert len(first.get("/public/timeline?limit=1").json()["recaps"]) == 1
    finally:
        set_engine(previous)


def test_director_does_not_repeat_an_unchanged_rejected_invitation():
    engine = SimulationEngine()
    goal = choose(engine, StoryCategory.ROMANCE_OPPORTUNITY)
    engine.tick()
    assert resolved(engine).result.outcome == "refusal"
    rejected_pair = set(goal.eligible_characters)
    for _ in range(12):
        engine.tick()
        current = resolved(engine)
        if current.category == StoryCategory.ROMANCE_OPPORTUNITY:
            assert (
                set(current.eligible_characters) != rejected_pair
                or current.result.outcome != "refusal"
            )
