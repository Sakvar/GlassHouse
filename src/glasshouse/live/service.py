from __future__ import annotations

import json
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from glasshouse.live.i18n import NAMES, STATUS, STRINGS, episode_view, goal_view
from glasshouse.live.models import Budget, LLMRun, RecapRow, Season, ShowEventRow, VoteRow, now
from glasshouse.live.narrator import OpenRouterNarrator
from glasshouse.live.schemas import Character, Episode, GoalsView, Page, SeasonView, VoteReceipt
from glasshouse.show.models import ViewerVote
from glasshouse.simulation.engine import SimulationEngine
from glasshouse.simulation.replay import replay_from
from glasshouse.simulation.snapshot import SimulationSnapshot


class DomainError(Exception):
    def __init__(self, code, status=409):
        self.code = code
        self.status = status
        super().__init__(code)


class ShowService:
    def __init__(self, sessions, settings, narrator=None):
        self.sessions = sessions
        self.settings = settings
        self.narrator = narrator or OpenRouterNarrator(settings)

    def ensure_season(self):
        with self.sessions() as db:
            if db.get(Season, "villa-1"):
                return
        engine = SimulationEngine(seed=42)
        try:
            with self.sessions.begin() as db:
                row = Season(
                    id="villa-1",
                    slug="villa",
                    config={"locale": self.settings.season_locale},
                    snapshot=engine.snapshot().model_dump(mode="json"),
                    revision=0,
                    next_tick_at=now() + timedelta(seconds=self.settings.tick_seconds),
                )
                db.add(row)
                db.flush()
                self._append(db, row, engine, 0)
        except IntegrityError:
            # Another startup may have won the unique season ID race.
            with self.sessions() as db:
                if not db.get(Season, "villa-1"):
                    raise

    def _load(self, db, season_id="villa-1"):
        row = db.get(Season, season_id)
        if row is None:
            raise DomainError("missing", 404)
        engine = replay_from(SimulationSnapshot.model_validate(row.snapshot), [], ticks=0)
        return row, engine

    def _reserve(self, db, row, expected_revision=None):
        revision = row.revision if expected_revision is None else expected_revision
        if row.revision != revision:
            raise DomainError("conflict")
        changed = db.execute(
            update(Season)
            .where(
                Season.id == row.id,
                Season.revision == revision,
            )
            .values(revision=revision + 1, updated_at=now()),
            execution_options={"synchronize_session": False},
        )
        if changed.rowcount != 1:
            raise DomainError("conflict")
        row.revision = revision + 1

    def _append(self, db, row, engine, old_length):
        for sequence, event in enumerate(engine.show.journal[old_length:], old_length + 1):
            db.add(
                ShowEventRow(
                    season_id=row.id,
                    sequence=sequence,
                    revision=row.revision,
                    tick=event.tick,
                    kind=event.kind,
                    source=event.source,
                    payload={
                        **event.model_dump(exclude={"data_json"}),
                        "data": json.loads(event.data_json),
                    },
                )
            )

    def _save(self, db, row, engine, old_length):
        self._append(db, row, engine, old_length)
        row.snapshot = engine.snapshot().model_dump(mode="json")
        db.flush()

    def tick(self, season_id="villa-1", expected_revision=None, due_only=False):
        with self.sessions.begin() as db:
            row, engine = self._load(db, season_id)
            if row.status != "active" or (due_only and row.next_tick_at > now()):
                return False
            self._reserve(db, row, expected_revision)
            old_length = len(engine.show.journal)
            engine.tick()
            translations = {loc: episode_view(engine, loc) for loc in ("ru", "en")}
            locale = row.config["locale"]
            previous = db.get(RecapRow, (row.id, engine.world.tick - 1))
            previous = Episode.model_validate(previous.translations[locale]) if previous else None
            goal = next(
                (g for g in engine.show.goals if g.result and g.tick == engine.world.tick), None
            )
            translations[locale], audit = self.narrator.narrate(
                translations[locale],
                goal.category.value if goal else "conversation",
                previous,
            )
            db.add(LLMRun(season_id=row.id, tick=engine.world.tick, **audit))
            db.add(
                RecapRow(
                    season_id=row.id,
                    tick=engine.world.tick,
                    translations={
                        loc: ep.model_dump(mode="json") for loc, ep in translations.items()
                    },
                )
            )
            row.next_tick_at = now() + timedelta(seconds=self.settings.tick_seconds)
            self._save(db, row, engine, old_length)
        return True

    def due(self):
        with self.sessions() as db:
            return list(
                db.execute(
                    select(Season.id, Season.revision).where(
                        Season.status == "active",
                        Season.next_tick_at <= now(),
                    )
                ).all()
            )

    def _remaining(self, db, user_id, tick, season_id="villa-1"):
        if not user_id:
            return None
        budget = db.get(Budget, (season_id, user_id, tick))
        return 3 - (budget.spent if budget else 0)

    def vote(self, user_id, vote):
        with self.sessions.begin() as db:
            row, engine = self._load(db)
            # Reserve the season before inspecting or changing its shared budget.
            self._reserve(db, row)
            duplicate = db.scalar(
                select(VoteRow).where(
                    VoteRow.season_id == row.id,
                    VoteRow.user_id == user_id,
                    VoteRow.request_id == vote.request_id,
                )
            )
            if duplicate:
                if (duplicate.tick, duplicate.goal_id, duplicate.points) != (
                    vote.tick,
                    vote.story_goal_id,
                    vote.influence_points,
                ):
                    raise DomainError("conflict")
                return VoteReceipt(
                    duplicate=True,
                    tick=vote.tick,
                    remaining=self._remaining(db, user_id, vote.tick),
                )
            goal = next((g for g in engine.show.goals if g.id == vote.story_goal_id), None)
            if goal is None:
                raise DomainError("missing", 404)
            if (
                row.status != "active"
                or goal.status != "active"
                or vote.tick != engine.world.tick + 1
            ):
                raise DomainError("conflict")
            budget = db.get(Budget, (row.id, user_id, vote.tick))
            if budget is None:
                budget = Budget(season_id=row.id, user_id=user_id, tick=vote.tick, spent=0)
                db.add(budget)
                db.flush()
            changed = db.execute(
                update(Budget)
                .where(
                    Budget.season_id == row.id,
                    Budget.user_id == user_id,
                    Budget.tick == vote.tick,
                    Budget.spent + vote.influence_points <= 3,
                )
                .values(spent=Budget.spent + vote.influence_points)
            )
            if changed.rowcount != 1:
                raise DomainError("budget")
            old_length = len(engine.show.journal)
            engine.show.vote(
                ViewerVote(
                    viewer_id=user_id,
                    story_goal_id=vote.story_goal_id,
                    tick=vote.tick,
                    influence_points=vote.influence_points,
                )
            )
            db.add(
                VoteRow(
                    id=str(uuid4()),
                    season_id=row.id,
                    user_id=user_id,
                    tick=vote.tick,
                    goal_id=vote.story_goal_id,
                    points=vote.influence_points,
                    request_id=vote.request_id,
                )
            )
            self._save(db, row, engine, old_length)
            return VoteReceipt(tick=vote.tick, remaining=self._remaining(db, user_id, vote.tick))

    def view(self, locale="ru", user_id=None):
        with self.sessions() as db:
            row, engine = self._load(db)
            recap = db.get(RecapRow, (row.id, engine.world.tick))
            state = engine.show.public_state()
            season = SeasonView(
                season_id=row.id,
                setting=STRINGS[locale]["villa"],
                locale=locale,
                tick=state.tick,
                voting_tick=state.voting_tick,
                tick_minutes=state.tick_minutes,
                sim_time=state.sim_time,
                revision=row.revision,
                next_tick_at=row.next_tick_at.isoformat() + "Z",
                latest_recap=Episode.model_validate(recap.translations[locale]) if recap else None,
                characters=[
                    Character(
                        id=c.id,
                        name=NAMES[locale][c.id],
                        location=STATUS[locale].get(c.location, STRINGS[locale]["villa"]),
                        activity=STATUS[locale].get(c.activity, STATUS[locale]["idle"]),
                        mood=STATUS[locale].get(c.mood, STATUS[locale]["neutral"]),
                    )
                    for c in state.characters
                ],
            )
            goals = GoalsView(
                goals=[goal_view(g, locale) for g in engine.show.active_goals()],
                tick=state.voting_tick,
                remaining=self._remaining(db, user_id, state.voting_tick),
            )
            return season, goals

    def history(self, locale="ru", page=1, limit=10, from_tick=0):
        with self.sessions() as db:
            where = (RecapRow.season_id == "villa-1", RecapRow.tick >= from_tick)
            total = db.scalar(select(func.count()).select_from(RecapRow).where(*where))
            rows = db.scalars(
                select(RecapRow)
                .where(*where)
                .order_by(RecapRow.tick.desc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
            episodes = [Episode.model_validate(r.translations[locale]) for r in rows]
            return Page(
                items=episodes,
                recaps=episodes,
                page=page,
                limit=limit,
                total=total,
                has_next=page * limit < total,
            )
