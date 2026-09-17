"""Isolated integration smoke test; run explicitly against local Compose PostgreSQL."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from alembic import command
from glasshouse.live.auth import AuthService, Registration
from glasshouse.live.config import Settings
from glasshouse.live.db import connect
from glasshouse.live.models import Season, ShowEventRow, now
from glasshouse.live.schemas import VoteInput
from glasshouse.live.service import DomainError, ShowService
from glasshouse.live.worker import run_once


def main():
    settings = replace(Settings.from_env(), llm_enabled=False)
    if not settings.database_url.startswith("postgresql"):
        raise SystemExit("This smoke check requires PostgreSQL")
    schema = "smoke_" + uuid4().hex
    admin = create_engine(settings.database_url)
    with admin.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA {schema}"))
    previous_url = os.environ.get("DATABASE_URL")
    engine = None
    try:
        url = make_url(settings.database_url).update_query_dict(
            {"options": f"-csearch_path={schema}"}
        )
        os.environ["DATABASE_URL"] = url.render_as_string(hide_password=False)
        command.upgrade(Config("alembic.ini"), "head")
        settings = replace(Settings.from_env(), llm_enabled=False)
        engine, sessions = connect(settings.database_url)
        service = ShowService(sessions, settings)
        service.ensure_season()
        auth = AuthService(sessions, settings.session_secret)
        user = auth.register(
            Registration(
                email="smoke@example.com", display_name="Smoke", password=uuid4().hex, locale="en"
            )
        )
        goal = service.view()[1].goals[0]
        vote = VoteInput(
            story_goal_id=goal.id, tick=goal.tick, influence_points=2, request_id=uuid4().hex
        )
        assert service.vote(user.id, vote).remaining == 1
        assert service.vote(user.id, vote).duplicate

        def cast(_):
            try:
                service.vote(
                    user.id,
                    vote.model_copy(update={"request_id": uuid4().hex, "influence_points": 1}),
                )
                return 1
            except DomainError:
                return 0

        with ThreadPoolExecutor(max_workers=4) as pool:
            assert sum(pool.map(cast, range(4))) == 1
        assert service.view(user_id=user.id)[1].remaining == 0
        with sessions.begin() as db:
            db.get(Season, "villa-1").next_tick_at = now() - timedelta(seconds=5)
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sum(pool.map(lambda _: run_once(service), range(2))) == 1
        assert service.view()[0].tick == 1
        original = service._save
        with sessions() as db:
            before = db.scalar(select(func.count()).select_from(ShowEventRow))

        def fail(*args):
            original(*args)
            raise RuntimeError("rollback check")

        service._save = fail
        try:
            service.tick()
            raise AssertionError("Injected failure was not raised")
        except RuntimeError:
            pass
        engine.dispose()
        engine, sessions = connect(settings.database_url)
        service = ShowService(sessions, settings)
        assert service.view()[0].tick == 1 and service.history().total == 1
        with sessions() as db:
            assert db.scalar(select(func.count()).select_from(ShowEventRow)) == before
        try:
            with sessions.begin() as db:
                db.execute(text("DELETE FROM show_events"))
            raise AssertionError("Append-only trigger did not reject deletion")
        except DBAPIError:
            pass
        print(
            "PASS PostgreSQL: migrations, voting, budget, concurrency, rollback, restart, journal"
        )
    finally:
        if engine:
            engine.dispose()
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url
        with admin.begin() as connection:
            connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        admin.dispose()


if __name__ == "__main__":
    main()
