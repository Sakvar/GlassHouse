"""Gossip chain acceptance scenario runner."""

from __future__ import annotations

from glasshouse.agents.seeds import create_seed_agents
from glasshouse.cognition.beliefs import Belief
from glasshouse.cognition.claims import Claim, ClaimPredicate, derive_claim
from glasshouse.cognition.perception import perceive_event, write_knowledge
from glasshouse.cognition.pipeline import run_cognition
from glasshouse.cognition.triggers import TRIGGER_PRIORITIES, CognitionTrigger
from glasshouse.llm.schemas import (
    AppraisalIntent,
    BeliefUpdateIntent,
    FormClaimIntent,
    StartConversationIntent,
    UtteranceIntent,
)
from glasshouse.llm.stub import ScriptedStubLLM
from glasshouse.relationships.models import SemanticAppraisal
from glasshouse.simulation.engine import SimulationEngine
from glasshouse.world.house import create_initial_world
from glasshouse.world.models import Activity, AgentRef, WorldEvent


def _match(agent_id: str, schema: type, predicate: str | None = None, trigger: str | None = None):
    def matcher(ctx, sch):
        if ctx.agent_id != agent_id or sch != schema:
            return False
        if predicate and predicate not in ctx.predicates:
            return False
        if trigger and ctx.trigger_type != trigger:
            return False
        return True

    return matcher


def run_gossip_scenario() -> tuple[SimulationEngine, ScriptedStubLLM, float, WorldEvent]:
    agents = create_seed_agents()
    agents["max"].ref = AgentRef(
        agent_id="max", location_id="bedroom_a", activity=Activity.CONVERSING
    )
    agents["dan"].ref = AgentRef(
        agent_id="dan", location_id="bedroom_a", activity=Activity.CONVERSING
    )
    agents["lea"].ref = AgentRef(
        agent_id="lea", location_id="living_room", activity=Activity.IDLE, attention=0.85
    )
    agents["eva"].ref = AgentRef(agent_id="eva", location_id="living_room", activity=Activity.IDLE)

    truth_claim = Claim(
        id="truth_claim_max",
        subject="max",
        predicate=ClaimPredicate.BORROWED_MONEY_UNREPAID,
        speaker_id="max",
        specificity=1.0,
    )

    lea_claim = Claim(
        subject="max",
        predicate=ClaimPredicate.BORROWED_MONEY_UNREPAID,
        holder_id="lea",
        evidence_ids=[],
        specificity=0.8,
    )

    lea_gossip_claim = derive_claim(
        lea_claim,
        ClaimPredicate.UNRELIABLE_WITH_MONEY,
        speaker_id="lea",
        tick=2,
        distortion_type="imprecision",
        holder_id="lea",
        evidence_ids=[],
        specificity=0.5,
    )

    eva_belief = Belief(
        subject="max",
        predicate=ClaimPredicate.UNRELIABLE_WITH_MONEY,
        confidence=0.6,
        source="overheard",
        evidence_ids=[],
        supporting_claim_ids=[lea_gossip_claim.id],
    )

    eva_gossip_claim = derive_claim(
        Claim(
            subject="max",
            predicate=ClaimPredicate.UNRELIABLE_WITH_MONEY,
            holder_id="eva",
            id=lea_gossip_claim.id,
        ),
        ClaimPredicate.HAS_MONEY_PROBLEMS,
        speaker_id="eva",
        tick=4,
        distortion_type="reframe",
        holder_id="eva",
        evidence_ids=[],
        specificity=0.3,
    )

    expectations = [
        (
            _match(
                "lea",
                FormClaimIntent,
                ClaimPredicate.BORROWED_MONEY_UNREPAID.value,
                "truth_admission",
            ),
            FormClaimIntent(claim=lea_claim),
        ),
        (
            _match("lea", StartConversationIntent),
            StartConversationIntent(target="eva", participants=["lea", "eva"]),
        ),
        (
            _match("lea", UtteranceIntent, ClaimPredicate.UNRELIABLE_WITH_MONEY.value),
            UtteranceIntent(
                claim=lea_gossip_claim,
                exact_text="I think Max is unreliable with money",
                target="eva",
                volume=0.7,
            ),
        ),
        (
            _match("eva", BeliefUpdateIntent, ClaimPredicate.UNRELIABLE_WITH_MONEY.value),
            BeliefUpdateIntent(belief=eva_belief),
        ),
        (
            _match("eva", StartConversationIntent),
            StartConversationIntent(target="dan", participants=["eva", "dan"]),
        ),
        (
            _match("eva", UtteranceIntent, ClaimPredicate.HAS_MONEY_PROBLEMS.value),
            UtteranceIntent(
                claim=eva_gossip_claim,
                exact_text="I heard Max has money problems",
                target="dan",
                volume=0.7,
            ),
        ),
        (
            _match("dan", AppraisalIntent, ClaimPredicate.HAS_MONEY_PROBLEMS.value),
            AppraisalIntent(
                appraisal=SemanticAppraisal(
                    target_id="max",
                    trust_shift="negative",
                    rationale="Eva said Max has money problems",
                )
            ),
        ),
    ]

    stub = ScriptedStubLLM(expectations)
    world = create_initial_world()
    for aid, ref in [
        ("max", agents["max"].ref),
        ("dan", agents["dan"].ref),
        ("lea", agents["lea"].ref),
        ("eva", agents["eva"].ref),
    ]:
        world.agents[aid] = ref

    engine = SimulationEngine(world=world, agents=agents, seed=42, llm=stub)
    starting_trust = agents["dan"].get_relationship("max").trust

    truth_event = engine.emit_truth_admission("max", truth_claim, volume=0.4)
    engine.world.append_event(truth_event)

    lea_knowledge_entries = perceive_event(engine.world, truth_event)
    lea_entry = next(e for e in lea_knowledge_entries if e.agent_id == "lea")
    write_knowledge(agents["lea"].knowledge, lea_entry)
    lea_claim.evidence_ids = [lea_entry.id]
    lea_gossip_claim.evidence_ids = [lea_entry.id]

    trigger = CognitionTrigger(
        agent_id="lea",
        trigger_type="truth_admission",
        tick=1,
        priority=TRIGGER_PRIORITIES.get("truth_admission", 10),
        context={
            "predicates": [ClaimPredicate.BORROWED_MONEY_UNREPAID.value],
            "event_id": truth_event.id,
        },
        knowledge_entry=lea_entry,
    )
    intent = run_cognition(agents["lea"], trigger, stub, FormClaimIntent, world.locations)
    if intent:
        engine.apply_intent("lea", intent)

    trigger = CognitionTrigger(
        agent_id="lea",
        trigger_type="goal_active",
        tick=2,
        context={"target_id": "eva", "predicates": []},
    )
    intent = run_cognition(agents["lea"], trigger, stub, StartConversationIntent, world.locations)
    if intent:
        for ev in engine.apply_intent("lea", intent):
            engine.world.append_event(ev)

    trigger = CognitionTrigger(
        agent_id="lea",
        trigger_type="scene_turn",
        tick=3,
        context={"predicates": [ClaimPredicate.UNRELIABLE_WITH_MONEY.value]},
    )
    intent = run_cognition(agents["lea"], trigger, stub, UtteranceIntent, world.locations)
    lea_utterance_event = None
    if intent:
        for ev in engine.apply_intent("lea", intent):
            engine.world.append_event(ev)
            lea_utterance_event = ev

    if lea_utterance_event:
        eva_entries = perceive_event(engine.world, lea_utterance_event)
        eva_entry = next((e for e in eva_entries if e.agent_id == "eva"), None)
        if eva_entry:
            write_knowledge(agents["eva"].knowledge, eva_entry)
            eva_belief.evidence_ids = [eva_entry.id]

    trigger = CognitionTrigger(
        agent_id="eva",
        trigger_type="overheard",
        tick=4,
        context={"predicates": [ClaimPredicate.UNRELIABLE_WITH_MONEY.value]},
    )
    intent = run_cognition(agents["eva"], trigger, stub, BeliefUpdateIntent, world.locations)
    if intent:
        engine.apply_intent("eva", intent)

    trigger = CognitionTrigger(
        agent_id="eva",
        trigger_type="goal_active",
        tick=5,
        context={"target_id": "dan", "predicates": []},
    )
    intent = run_cognition(agents["eva"], trigger, stub, StartConversationIntent, world.locations)
    if intent:
        agents["eva"].ref = agents["eva"].ref.model_copy(update={"activity": Activity.CONVERSING})
        agents["dan"].ref = agents["dan"].ref.model_copy(
            update={"location_id": "living_room", "activity": Activity.CONVERSING}
        )
        world.agents["dan"] = agents["dan"].ref
        for ev in engine.apply_intent("eva", intent):
            engine.world.append_event(ev)

    trigger = CognitionTrigger(
        agent_id="eva",
        trigger_type="scene_turn",
        tick=6,
        context={"predicates": [ClaimPredicate.HAS_MONEY_PROBLEMS.value]},
    )
    intent = run_cognition(agents["eva"], trigger, stub, UtteranceIntent, world.locations)
    eva_utterance_event = None
    if intent:
        for ev in engine.apply_intent("eva", intent):
            engine.world.append_event(ev)
            eva_utterance_event = ev

    if eva_utterance_event:
        dan_entries = perceive_event(engine.world, eva_utterance_event)
        dan_entry = next((e for e in dan_entries if e.agent_id == "dan"), None)
        if dan_entry:
            write_knowledge(agents["dan"].knowledge, dan_entry)

    trigger = CognitionTrigger(
        agent_id="dan",
        trigger_type="overheard",
        tick=7,
        context={"predicates": [ClaimPredicate.HAS_MONEY_PROBLEMS.value]},
    )
    intent = run_cognition(agents["dan"], trigger, stub, AppraisalIntent, world.locations)
    if intent:
        engine.apply_intent("dan", intent)

    stub.assert_exhausted()
    return engine, stub, starting_trust, truth_event
