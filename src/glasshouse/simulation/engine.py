from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

from glasshouse.agents.seeds import create_seed_agents, sync_agent_refs
from glasshouse.agents.state import AgentState
from glasshouse.cognition.claims import Claim, ClaimPredicate, derive_claim
from glasshouse.cognition.perception import perceive_event, write_knowledge
from glasshouse.cognition.pipeline import run_cognition
from glasshouse.cognition.triggers import CognitionTrigger, TRIGGER_PRIORITIES
from glasshouse.events.queue import EventQueue
from glasshouse.llm.provider import LLMProvider, ModelTier
from glasshouse.llm.schemas import (
    AppraisalIntent,
    BeliefUpdateIntent,
    FormClaimIntent,
    Intent,
    SceneSummary,
    StartConversationIntent,
    UtteranceIntent,
)
from glasshouse.llm.stub import ScriptedStubLLM
from glasshouse.memory.stores import WorkingMemoryItem
from glasshouse.relationships.appraisal_rules import apply_appraisal
from glasshouse.scenes.manager import SceneManager
from glasshouse.scenes.models import SemanticChange
from glasshouse.simulation.drama import DramaScore, score_drama
from glasshouse.simulation.snapshot import SimulationSnapshot
from glasshouse.world.actions import (
    create_truth_admission_event,
    create_utterance_event,
    move_agent,
    set_activity,
)
from glasshouse.world.house import create_initial_world
from glasshouse.world.models import Activity, WorldEvent, WorldEventType
from glasshouse.world.perception import PerceptionLevel


class SimulationEngine:
    def __init__(
        self,
        world=None,
        agents: dict[str, AgentState] | None = None,
        seed: int = 42,
        llm: LLMProvider | None = None,
    ) -> None:
        self.world = world or create_initial_world()
        self.agents = agents or create_seed_agents()
        self.rng = random.Random(seed)
        self.seed = seed
        self.llm = llm or ScriptedStubLLM([])
        self.event_queue = EventQueue()
        self.scene_manager = SceneManager()
        self.drama_scores: list[DramaScore] = []
        self._init_world_agents()
        self._semantic_change = SemanticChange()
        self._knowledge_only_turn = False

    def _init_world_agents(self) -> None:
        for agent_id, state in self.agents.items():
            self.world.agents[agent_id] = state.ref

    def _advance_time(self, delta_minutes: int = 1) -> None:
        self.world.tick += 1
        dt = datetime.fromisoformat(self.world.sim_time) + timedelta(minutes=delta_minutes)
        self.world.sim_time = dt.isoformat()

    def inject_event(self, event: WorldEvent) -> None:
        self.event_queue.enqueue_world(event, tick=self.world.tick, priority=0)

    def emit_truth_admission(
        self,
        actor_id: str,
        claim: Claim,
        volume: float = 0.4,
    ) -> WorldEvent:
        claim.holder_id = actor_id
        self.agents[actor_id].claims.add(claim)
        event = create_truth_admission_event(
            self.world, actor_id, claim.id, volume=volume
        )
        self.inject_event(event)
        return event

    def process_perception(self, event: WorldEvent) -> list[CognitionTrigger]:
        triggers: list[CognitionTrigger] = []
        entries = perceive_event(self.world, event)
        for entry in entries:
            agent = self.agents[entry.agent_id]
            write_knowledge(agent.knowledge, entry)
            agent.memory.add_working(
                WorkingMemoryItem(
                    tick=self.world.tick,
                    sim_time=self.world.sim_time,
                    content=entry.sensory_content.snippet,
                    subject=entry.sensory_content.actor,
                    event_id=entry.event_id,
                    claim_id=entry.sensory_content.claim_id,
                ),
                self.world.sim_time,
            )

            trigger_type = "overheard"
            priority = TRIGGER_PRIORITIES.get("overheard", 20)
            if event.type == WorldEventType.TRUTH_ADMISSION:
                trigger_type = "truth_admission"
                priority = TRIGGER_PRIORITIES.get("truth_admission", 10)

            predicates: list[str] = []
            claim_id = entry.sensory_content.claim_id
            if claim_id:
                for a in self.agents.values():
                    c = a.claims.get(claim_id)
                    if c:
                        predicates.append(c.predicate.value)

            triggers.append(
                CognitionTrigger(
                    agent_id=entry.agent_id,
                    trigger_type=trigger_type,
                    tick=self.world.tick,
                    priority=priority,
                    context={
                        "predicates": predicates,
                        "event_id": event.id,
                        "claim_id": claim_id,
                        "perception_level": entry.perception_level.value,
                    },
                    knowledge_entry=entry,
                )
            )
        return triggers

    def apply_intent(self, agent_id: str, intent: Intent) -> list[WorldEvent]:
        agent = self.agents[agent_id]
        events: list[WorldEvent] = []

        if isinstance(intent, FormClaimIntent):
            claim = intent.claim
            claim.holder_id = agent_id
            agent.claims.add(claim)
            self._semantic_change.claims_changed = True

        elif isinstance(intent, BeliefUpdateIntent):
            agent.beliefs.add(intent.belief)
            self._semantic_change.beliefs_changed = True

        elif isinstance(intent, AppraisalIntent):
            target_id = intent.appraisal.target_id
            current = agent.get_relationship(target_id)
            updated = apply_appraisal(current, intent.appraisal, agent.personality)
            agent.relationships[target_id] = updated
            self._semantic_change.relationships_changed = True

        elif isinstance(intent, StartConversationIntent):
            location = agent.ref.location_id
            participants = intent.participants or (
                [agent_id, intent.target] if intent.target else [agent_id]
            )
            observers = [
                aid for aid, ref in self.world.agents.items()
                if ref.location_id == location and aid not in participants
            ]
            scene = self.scene_manager.start_scene(
                location, participants, observers, self.world.sim_time, topic=intent.rationale
            )
            for pid in participants:
                if pid in self.agents:
                    self.agents[pid].ref = self.agents[pid].ref.model_copy(
                        update={"activity": Activity.CONVERSING}
                    )
                    self.world.agents[pid] = self.agents[pid].ref
            event = WorldEvent(
                id=f"scene_{scene.id}",
                tick=self.world.tick,
                type=WorldEventType.SCENE_STARTED,
                actor=agent_id,
                location=location,
                payload={"scene_id": scene.id, "participants": participants},
            )
            events.append(event)

        elif isinstance(intent, UtteranceIntent):
            claim = intent.claim
            claim.speaker_id = agent_id
            claim.holder_id = agent_id
            agent.claims.add(claim)
            event = create_utterance_event(
                self.world,
                agent_id,
                claim.id,
                intent.exact_text,
                volume=intent.volume,
                target_id=intent.target,
            )
            events.append(event)
            self._semantic_change.claims_changed = True

            active = self.scene_manager.get_active_at(agent.ref.location_id)
            if active:
                self.scene_manager.record_utterance(active.id, event.id)

        elif intent.intent_type.value == "move" and intent.target:
            event, updated = move_agent(self.world, agent_id, intent.target)
            agent.ref = updated
            self.world.agents[agent_id] = updated
            events.append(event)

        return events

    def _resolve_intent_schema(self, trigger: CognitionTrigger) -> type[Intent]:
        predicates = trigger.context.get("predicates", [])
        if trigger.trigger_type == "truth_admission" or ClaimPredicate.BORROWED_MONEY_UNREPAID.value in predicates:
            return FormClaimIntent
        if ClaimPredicate.UNRELIABLE_WITH_MONEY.value in predicates:
            return BeliefUpdateIntent
        if ClaimPredicate.HAS_MONEY_PROBLEMS.value in predicates:
            return AppraisalIntent
        if trigger.context.get("target_id"):
            return StartConversationIntent
        return UtteranceIntent

    def process_cognition_triggers(self, triggers: list[CognitionTrigger]) -> None:
        sorted_triggers = sorted(triggers, key=lambda t: (t.tick, t.priority, t.agent_id))
        for trigger in sorted_triggers:
            agent = self.agents[trigger.agent_id]
            schema = self._resolve_intent_schema(trigger)
            try:
                intent = run_cognition(
                    agent, trigger, self.llm, schema, self.world.locations
                )
            except Exception:
                continue
            if intent is None:
                continue
            new_events = self.apply_intent(trigger.agent_id, intent)
            for event in new_events:
                self.world.append_event(event)
                new_triggers = self.process_perception(event)
                self.process_cognition_triggers(new_triggers)

    def process_scenes(self) -> None:
        for scene in self.scene_manager.active_scenes():
            should_collapse = self.scene_manager.advance_turn(
                scene.id,
                self._semantic_change,
                knowledge_only=self._knowledge_only_turn,
            )
            if should_collapse:
                summary = SceneSummary(
                    scene_id=scene.id,
                    summary=f"Conversation at {scene.location}",
                    key_claim_ids=[],
                    participants=scene.participants,
                )
                if hasattr(self.llm, "generate_structured"):
                    try:
                        from glasshouse.llm.provider import LLMCallContext
                        summary = self.llm.generate_structured(
                            LLMCallContext(
                                agent_id=scene.participants[0],
                                trigger_type="scene_collapse",
                                schema_name="SceneSummary",
                                tick=self.world.tick,
                            ),
                            SceneSummary,
                            ModelTier.FAST,
                        )
                    except Exception:
                        pass
                memory = self.scene_manager.collapse_scene(scene.id, summary, self.world.tick)
                for pid in scene.participants:
                    if pid in self.agents:
                        self.agents[pid].memory.add_episodic(memory)
                collapse_event = WorldEvent(
                    id=f"collapse_{scene.id}",
                    tick=self.world.tick,
                    type=WorldEventType.SCENE_COLLAPSED,
                    location=scene.location,
                    payload={"scene_id": scene.id},
                )
                self.world.append_event(collapse_event)

    def tick(self, delta_minutes: int = 1) -> list[WorldEvent]:
        self._semantic_change = SemanticChange()
        self._knowledge_only_turn = False
        tick_events: list[WorldEvent] = []

        self._advance_time(delta_minutes)

        pending = self.event_queue.drain_world_events(self.world.tick)
        all_triggers: list[CognitionTrigger] = []

        for event in pending:
            self.world.append_event(event)
            tick_events.append(event)
            triggers = self.process_perception(event)
            all_triggers.extend(triggers)

        self.process_cognition_triggers(all_triggers)
        self.process_scenes()
        self.drama_scores = score_drama(self.agents, self.world)

        return tick_events

    def snapshot(self) -> SimulationSnapshot:
        return SimulationSnapshot(
            tick=self.world.tick,
            sim_time=self.world.sim_time,
            seed=self.seed,
            world=self.world.model_copy(deep=True),
            agents={k: v.model_copy(deep=True) for k, v in self.agents.items()},
            drama_scores=self.drama_scores,
        )

    def run(self, hours: float = 48, ticks_per_hour: int = 60) -> None:
        total_ticks = int(hours * ticks_per_hour)
        for _ in range(total_ticks):
            self.tick()
