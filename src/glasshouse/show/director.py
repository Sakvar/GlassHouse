from __future__ import annotations

import hashlib
from collections import deque
from typing import TYPE_CHECKING

from glasshouse.cognition.claims import Claim, ClaimPredicate, derive_claim
from glasshouse.cognition.validator import validate_intent
from glasshouse.llm.schemas import Intent, IntentType
from glasshouse.show.models import (
    GoalStatus,
    PublicCharacter,
    PublicSeason,
    PublicTimeline,
    Recap,
    RelationshipChange,
    ShowEvent,
    StoryCategory,
    StoryGoal,
    StoryResult,
    TimelineItem,
    ViewerVote,
)
from glasshouse.world.actions import set_activity
from glasshouse.world.models import Activity, WorldEvent, WorldEventType
from glasshouse.world.perception import PerceptionLevel

if TYPE_CHECKING:
    from glasshouse.simulation.engine import SimulationEngine


TITLES = {
    StoryCategory.CONVERSATION: "Время поговорить",
    StoryCategory.ROMANCE_OPPORTUNITY: "Приглашение на свидание",
    StoryCategory.REVEAL_SECRET: "Возможность раскрыть секрет",
    StoryCategory.CONFLICT: "Обсудить разногласия",
    StoryCategory.RECONCILIATION: "Шанс помириться",
}
SECRET_ID = "max_unpaid_debt"


class PublicShowDirector:
    """Versioned deterministic policy. The journal is the source of audience state."""

    def __init__(self, engine: SimulationEngine, journal: tuple[ShowEvent, ...] = ()):
        self.engine = engine
        self._journal: tuple[ShowEvent, ...] = ()
        self._goals: dict[str, StoryGoal] = {}
        self._votes: tuple[tuple[str, ViewerVote], ...] = ()
        self._recaps: tuple[Recap, ...] = ()
        for event in journal:
            self._apply(event)
        if not journal:
            self.open_goals()

    @property
    def journal(self) -> tuple[ShowEvent, ...]:
        return self._journal

    @property
    def recaps(self) -> tuple[Recap, ...]:
        return self._recaps

    @property
    def goals(self) -> tuple[StoryGoal, ...]:
        return tuple(self._goals.values())

    def active_goals(self) -> tuple[StoryGoal, ...]:
        return tuple(g for g in self.goals if g.status == GoalStatus.ACTIVE)

    def _apply(self, event: ShowEvent) -> None:
        if event.kind in ("goal_opened", "goal_selected", "goal_closed"):
            goal = StoryGoal.model_validate_json(event.data_json)
            self._goals[goal.id] = goal
        elif event.kind == "vote_cast":
            vote = ViewerVote.model_validate_json(event.data_json)
            self._votes += ((event.id, vote),)
            goal = self._goals[vote.story_goal_id]
            self._goals[goal.id] = goal.model_copy(
                update={"votes": goal.votes + vote.influence_points}
            )
        elif event.kind == "recap":
            self._recaps += (Recap.model_validate_json(event.data_json),)
        self._journal += (event,)

    def _record(self, kind, data, source="director:v1", cause_ids=()) -> ShowEvent:
        world = self.engine.world
        event = ShowEvent(
            id=f"show:{len(self._journal) + 1}",
            tick=world.tick,
            sim_time=world.sim_time,
            kind=kind,
            source=source,
            cause_ids=tuple(cause_ids),
            data_json=data.model_dump_json(),
        )
        self._apply(event)
        return event

    def vote(self, vote: ViewerVote) -> ShowEvent:
        with self.engine.lock:
            goal = self._goals.get(vote.story_goal_id)
            if goal is None:
                raise KeyError(vote.story_goal_id)
            if (
                goal.status != GoalStatus.ACTIVE
                or vote.tick != self.engine.world.tick + 1
                or goal.tick != vote.tick
            ):
                raise ValueError("Голосование за этот тик или цель закрыто")
            spent = sum(
                v.influence_points
                for _, v in self._votes
                if v.viewer_id == vote.viewer_id and v.tick == vote.tick
            )
            if spent + vote.influence_points > self.engine.show_config.influence_per_tick:
                raise ValueError("Превышен лимит бесплатного влияния на тик")
            opened = next(
                e.id
                for e in self._journal
                if e.kind == "goal_opened"
                and StoryGoal.model_validate_json(e.data_json).id == goal.id
            )
            return self._record("vote_cast", vote, "viewer", (opened,))

    def _tie_key(self, value: str, tick: int) -> str:
        return hashlib.sha256(f"{self.engine.seed}:{tick}:{value}".encode()).hexdigest()

    def _revealed(self) -> set[str]:
        return {sid for g in self.goals if g.result for sid in g.result.revealed_secret_ids}

    def _score(self, category: StoryCategory, aid: str, bid: str) -> float:
        agents = self.engine.agents
        a, b = agents[aid], agents[bid]
        ab, ba = a.get_relationship(bid), b.get_relationship(aid)
        score = 10 * (a.needs.social + b.needs.social)
        score += 4 if a.ref.location_id == b.ref.location_id else 0
        score += 3 if b.name.lower() in a.goals.today.lower() else 0
        if category == StoryCategory.CONVERSATION:
            score += 10 + a.personality.extraversion * 5
        elif category == StoryCategory.ROMANCE_OPPORTUNITY:
            score += (ab.attraction + ba.attraction) / 10 + a.needs.romantic * 5
        elif category == StoryCategory.REVEAL_SECRET:
            score += 20 + ab.trust / 10  # The seeded unpaid debt is an unfinished plot.
        elif category == StoryCategory.CONFLICT:
            score += (ab.resentment + ba.resentment - ab.affinity - ba.affinity) / 5
        elif category == StoryCategory.RECONCILIATION:
            score += (ab.resentment + ba.resentment) / 5 + (ab.trust + ba.trust) / 20
        for g in self.goals:
            if g.result and self.engine.world.tick - g.tick < 3:
                if g.category == category:
                    score -= 20
                if set(g.eligible_characters) == {aid, bid}:
                    score -= 15
        previous = next(
            (
                g
                for g in reversed(self.goals)
                if g.category == category and g.result and set(g.eligible_characters) == {aid, bid}
            ),
            None,
        )
        if previous and previous.result.outcome == "refusal" and self._refusal(previous):
            # Do not keep reissuing a rejected invitation when nothing made it viable.
            # Audience votes can still offer the circumstance; consent is checked again.
            score -= 50
        return round(score, 6)

    def open_goals(self) -> None:
        tick = self.engine.world.tick + 1
        ids = sorted(self.engine.agents)
        for category in StoryCategory:
            pairs = [(a, b) for a in ids for b in ids if a != b]
            if category == StoryCategory.ROMANCE_OPPORTUNITY:
                pairs = [
                    (a, b)
                    for a, b in pairs
                    if b in self.engine.agents[a].boundaries.romantic_partners
                    or a in self.engine.agents[b].boundaries.romantic_partners
                ]
            if category == StoryCategory.REVEAL_SECRET:
                pairs = [
                    (a, b)
                    for a, b in pairs
                    if a == "max"
                    and b == "dan"
                    and any(
                        s.id == SECRET_ID and s.other_character_id == b
                        for s in self.engine.agents[a].secrets
                    )
                    and SECRET_ID not in self._revealed()
                ]
            if not pairs:
                continue
            a, b = max(
                pairs,
                key=lambda pair: (
                    self._score(category, *pair),
                    self._tie_key(f"{category.value}:{pair}", tick),
                ),
            )
            goal = StoryGoal(
                id=f"goal:{tick}:{category.value}",
                title=TITLES[category],
                description=(
                    f"{self.engine.agents[a].name} и {self.engine.agents[b].name}: "
                    "предложить возможность. Каждый вправе отказаться."
                ),
                category=category,
                created_at=self.engine.world.sim_time,
                tick=tick,
                eligible_characters=(a, b),
                director_score=self._score(category, a, b),
            )
            self._record("goal_opened", goal)

    def select_goal(self) -> StoryGoal | None:
        active = [g for g in self.active_goals() if g.tick == self.engine.world.tick]
        if not active:
            return None
        voted = any(g.votes for g in active)
        winner = max(
            active,
            key=lambda g: (g.votes if voted else g.director_score, self._tie_key(g.id, g.tick)),
        )
        # All ballots in this round explain selection, including those for losing goals.
        causes = [eid for eid, v in self._votes if v.tick == winner.tick]
        selected = winner.model_copy(update={"status": GoalStatus.SELECTED})
        selection = self._record("goal_selected", selected, cause_ids=causes)
        for goal in active:
            if goal.id != winner.id:
                self._record(
                    "goal_closed",
                    goal.model_copy(
                        update={
                            "status": GoalStatus.EXPIRED,
                            "closed_at": self.engine.world.sim_time,
                        }
                    ),
                    cause_ids=(selection.id,),
                )
        return selected

    def _append_world(self, event: WorldEvent) -> WorldEvent:
        world = self.engine.world
        event = event.model_copy(update={"id": f"director:{world.tick}:{len(world.events_log)}"})
        world.append_event(event)
        # Perception writes evidence but does not ask an LLM to react to routine actions.
        self.engine.process_perception(event)
        return event

    def _meet(self, aid: str, bid: str) -> bool:
        """Walk a real route to the other character; never teleport."""
        engine = self.engine
        start = engine.agents[aid].ref.location_id
        dest = engine.agents[bid].ref.location_id
        queue = deque([(start, [])])
        seen = {start}
        route = None
        while queue:
            location, path = queue.popleft()
            if location == dest:
                route = path
                break
            for next_id in sorted(engine.world.locations[location].connected_to):
                if next_id not in seen:
                    seen.add(next_id)
                    queue.append((next_id, path + [next_id]))
        if route is None:
            return False
        for location in route:
            intent = validate_intent(
                engine.agents[aid],
                Intent(intent_type=IntentType.MOVE, target=location),
                engine.world.locations,
            )
            for event in engine.apply_intent(aid, intent):
                self._append_world(event)
        if route:
            event, ref = set_activity(engine.world, aid, Activity.IDLE)
            engine.agents[aid].ref = ref
            engine.world.agents[aid] = ref
            self._append_world(event)
        return True

    def _refusal(self, goal: StoryGoal) -> str | None:
        a, b = (self.engine.agents[x] for x in goal.eligible_characters)
        for person, other in ((a, b), (b, a)):
            boundary = person.boundaries
            if other.id in boundary.blocked_characters:
                return "personal_boundary"
            if not person.ref.capabilities.can_speak:
                return "unavailable"
            if not boundary.private_conversation_allowed:
                return "conversation_boundary"
        if goal.category == StoryCategory.ROMANCE_OPPORTUNITY:
            for person, other in ((a, b), (b, a)):
                boundary = person.boundaries
                relation = person.get_relationship(other.id)
                if not boundary.romance_allowed:
                    return "romance_boundary"
                if other.id not in boundary.romantic_partners:
                    return "incompatible_preferences"
                if (
                    relation.trust < boundary.minimum_trust
                    or relation.affinity < boundary.minimum_affinity
                    or relation.attraction < boundary.minimum_attraction
                ):
                    return "insufficient_mutual_connection"
        if goal.category == StoryCategory.REVEAL_SECRET:
            if not a.boundaries.secret_sharing_allowed or a.get_relationship(b.id).trust < 20:
                return "secret_boundary"
        if goal.category == StoryCategory.RECONCILIATION:
            if min(a.get_relationship(b.id).trust, b.get_relationship(a.id).trust) < -20:
                return "not_ready_to_reconcile"
        return None

    def _change(self, aid: str, bid: str, dimension: str, delta: float) -> RelationshipChange:
        agent = self.engine.agents[aid]
        relation = agent.get_relationship(bid)
        before = getattr(relation, dimension)
        minimum = 0 if dimension == "resentment" else -100
        after = max(minimum, min(100, before + delta))
        agent.relationships[bid] = relation.model_copy(update={dimension: after})
        self.engine._semantic_change.relationships_changed = True
        return RelationshipChange(
            actor_id=aid, target_id=bid, dimension=dimension, before=before, after=after
        )

    def _reveal_debt(self, aid: str) -> WorldEvent:
        """Only a fixed seed fact can be disclosed; no invented secrets or global knowledge."""
        engine = self.engine
        claim = Claim(
            id=f"secret:{SECRET_ID}",
            subject="max",
            object="dan",
            predicate=ClaimPredicate.BORROWED_MONEY_UNREPAID,
            holder_id=aid,
            speaker_id=aid,
        )
        event = self._append_world(
            WorldEvent(
                id="pending",
                tick=engine.world.tick,
                type=WorldEventType.TRUTH_ADMISSION,
                actor=aid,
                location=engine.agents[aid].ref.location_id,
                payload={
                    "claim_id": claim.id,
                    "exact_text": "Я взял у Дэна деньги и пока не вернул.",
                    "volume": 1.0,
                    "source": "seed:v1",
                    "secret_id": SECRET_ID,
                },
            )
        )
        claim.evidence_ids = [k.id for k in engine.agents[aid].knowledge.by_event(event.id)]
        engine.agents[aid].claims.add(claim)
        for person in engine.agents.values():
            for entry in person.knowledge.by_event(event.id):
                if person.id != aid and entry.perception_level == PerceptionLevel.FULL:
                    received = derive_claim(
                        claim,
                        claim.predicate,
                        aid,
                        engine.world.tick,
                        "faithful_report",
                        person.id,
                        [entry.id],
                        specificity=1.0,
                    )
                    received.id = f"{claim.id}:{person.id}:{engine.world.tick}"
                    person.claims.add(received)
        engine._semantic_change.claims_changed = True
        return event

    def play(self, goal: StoryGoal | None) -> StoryResult:
        engine = self.engine
        start = len(engine.world.events_log)
        if goal is None:
            return StoryResult(outcome="rest", reason="no_candidates", text="На вилле тихий час.")
        aid, bid = goal.eligible_characters
        a, b = engine.agents[aid], engine.agents[bid]
        changes = []
        secrets = ()
        reason = self._refusal(goal)
        if reason:
            outcome = "refusal"
            text = (
                f"{a.name} и {b.name}: предложено «{goal.title}», "
                "но встреча не состоялась — один из участников отказался или сейчас недоступен."
            )
        elif max(a.current.fatigue, b.current.fatigue) >= 0.85:
            outcome, reason = "rest", "needs_rest"
            text = f"{a.name} и {b.name} отложили разговор, чтобы отдохнуть."
        elif not self._meet(aid, bid):
            outcome, reason = "refusal", "no_route"
            text = f"{a.name} и {b.name} не смогли встретиться."
        else:
            reason = "mutual_choice"
            category = goal.category
            outcome, text = "conversation", f"{a.name} и {b.name} поговорили о жизни на вилле."
            dimensions = [("trust", 5), ("affinity", 4)]
            if category == StoryCategory.ROMANCE_OPPORTUNITY:
                outcome, text = (
                    "date",
                    f"{a.name} и {b.name} оба приняли приглашение на свидание "
                    "и провели время вместе.",
                )
                dimensions = [("trust", 4), ("affinity", 8)]
            elif category == StoryCategory.REVEAL_SECRET:
                self._reveal_debt(aid)
                outcome, text = "revelation", f"{a.name} признался: долг Дэну ещё не возвращён."
                secrets = (SECRET_ID,)
                dimensions = [("trust", 2)]
            elif category == StoryCategory.CONFLICT:
                outcome, text = (
                    "disagreement",
                    f"{a.name} и {b.name} поспорили о доверии и правилах совместной жизни.",
                )
                dimensions = [("trust", -4), ("resentment", 6)]
            elif category == StoryCategory.RECONCILIATION:
                outcome, text = (
                    "reconciliation",
                    f"{a.name} и {b.name} выслушали друг друга и решили попробовать помириться.",
                )
                dimensions = [("trust", 6), ("resentment", -8)]
            for actor, target in ((aid, bid), (bid, aid)):
                for dimension, delta in dimensions:
                    changes.append(self._change(actor, target, dimension, delta))
        # Needs/fatigue evolve without LLM calls; logged values explain future decisions.
        needs_after = {}
        for person in engine.agents.values():
            participating = person.id in (aid, bid)
            resting = outcome == "rest" or person.ref.activity == Activity.SLEEPING
            person.current.fatigue = round(
                max(0, min(1, person.current.fatigue + (-0.35 if resting else 0.1))), 6
            )
            person.needs.social = round(
                max(
                    0,
                    min(
                        1,
                        person.needs.social
                        + (-0.2 if participating and outcome not in ("rest", "refusal") else 0.08),
                    ),
                ),
                6,
            )
            person.current.mood = "thoughtful" if participating else person.current.mood
            needs_after[person.id] = {
                "fatigue": person.current.fatigue,
                "social": person.needs.social,
                "mood": person.current.mood,
            }
        result = StoryResult(
            outcome=outcome,
            reason=reason,
            text=text,
            relationship_changes=tuple(changes),
            revealed_secret_ids=secrets,
        )
        event = self._append_world(
            WorldEvent(
                id="pending",
                tick=engine.world.tick,
                type=WorldEventType.SHOW_ACTION,
                actor=aid,
                target=bid,
                location=a.ref.location_id,
                payload={
                    "source": "director:v1",
                    "story_goal_id": goal.id,
                    "category": goal.category.value,
                    "exact_text": text,
                    "result": result.model_dump(mode="json"),
                    "needs_after": needs_after,
                },
            )
        )
        result = result.model_copy(
            update={"event_ids": tuple(e.id for e in engine.world.events_log[start:])}
        )
        selection_id = next(e.id for e in reversed(self._journal) if e.kind == "goal_selected")
        self._record(
            "goal_closed",
            goal.model_copy(
                update={
                    "status": GoalStatus.RESOLVED,
                    "closed_at": engine.world.sim_time,
                    "result": result,
                }
            ),
            cause_ids=(selection_id, event.id),
        )
        return result

    def finish_tick(
        self,
        goal: StoryGoal | None,
        result: StoryResult,
        events: list[WorldEvent],
        relationship_changes: tuple[RelationshipChange, ...],
    ) -> Recap:
        reasons = {
            "refusal": "Личные границы определили исход; голос зрителя не заменяет согласие.",
            "rest": "Усталость отложила развитие отношений.",
            "revelation": (
                "Скрытый факт стал доступен свидетелям; теперь доверие можно обсудить открыто."
            ),
            "disagreement": "Напряжение выросло: у участников появился повод для примирения.",
        }
        recap = Recap(
            tick=self.engine.world.tick,
            sim_time=self.engine.world.sim_time,
            what_happened=(result.text,),
            why_it_matters=reasons.get(
                result.outcome, "Совместный выбор изменил доверие и симпатию участников."
            ),
            relationship_changes=relationship_changes,
            revealed_secret_ids=result.revealed_secret_ids,
            event_ids=tuple(e.id for e in events),
            story_goal_id=goal.id if goal else None,
        )
        self._record("recap", recap, "recap:v1", recap.event_ids)
        self.open_goals()
        return recap

    def public_state(self) -> PublicSeason:
        engine = self.engine
        return PublicSeason(
            tick=engine.world.tick,
            voting_tick=engine.world.tick + 1,
            sim_time=engine.world.sim_time,
            tick_minutes=engine.show_config.tick_minutes,
            influence_per_tick=engine.show_config.influence_per_tick,
            characters=tuple(
                PublicCharacter(
                    id=a.id,
                    name=a.name,
                    location=a.ref.location_id,
                    activity=a.ref.activity.value,
                    mood=a.current.mood,
                )
                for a in engine.agents.values()
            ),
            latest_recap=self.recaps[-1] if self.recaps else None,
        )

    def timeline(self, from_tick: int = 0, limit: int = 50) -> PublicTimeline:
        items = tuple(
            TimelineItem(
                tick=g.tick,
                sim_time=g.closed_at,
                story_goal_id=g.id,
                category=g.category,
                participants=g.eligible_characters,
                result=g.result,
            )
            for g in self.goals
            if g.result and g.tick >= from_tick
        )
        return PublicTimeline(
            items=items[-limit:],
            recaps=tuple(r for r in self.recaps if r.tick >= from_tick)[-limit:],
        )
