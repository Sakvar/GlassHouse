from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from apps.api.main import create_app
from glasshouse.live.auth import AuthService, Registration
from glasshouse.live.config import Settings
from glasshouse.live.db import connect
from glasshouse.live.models import (
    Budget,
    LLMRun,
    RecapRow,
    Season,
    ShowEventRow,
    User,
    VoteRow,
    now,
)
from glasshouse.live.schemas import VoteInput
from glasshouse.live.service import DomainError, ShowService
from glasshouse.live.worker import main, run_once
from glasshouse.simulation.replay import replay_from
from glasshouse.simulation.snapshot import SimulationSnapshot


@pytest.fixture
def storage(tmp_path, monkeypatch):
    url = "sqlite:///" + str(tmp_path / "beta.db")
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("LLM_ENABLED", "false")
    monkeypatch.setenv("APP_ENV", "test")
    command.upgrade(Config("alembic.ini"), "head")
    settings = Settings(database_url=url, app_env="development")
    engine, sessions = connect(url)
    show = ShowService(sessions, settings)
    show.ensure_season()
    yield settings, engine, sessions, show
    engine.dispose()


@pytest.fixture
def client(storage):
    with TestClient(create_app(storage[0])) as client:
        yield client


def token(client):
    return client.get("/public/session").json()["csrf_token"]


def register(client, email="viewer@example.com", locale="ru"):
    return client.post(
        "/register",
        data={
            "csrf": token(client),
            "email": email,
            "password": "A secure test password",
            "display_name": "Test Viewer",
            "locale": locale,
        },
    )


def vote_input(goal, points=1, request_id=None):
    return VoteInput(
        story_goal_id=goal.id,
        tick=goal.tick,
        influence_points=points,
        request_id=request_id or uuid4().hex,
    )


def add_user(sessions):
    auth = AuthService(sessions, "test-secret")
    return auth.register(
        Registration(
            email="viewer@example.com",
            password="a long password",
            display_name="Viewer",
            locale="ru",
        )
    )


def due(sessions):
    with sessions.begin() as db:
        db.get(Season, "villa-1").next_tick_at = now() - timedelta(seconds=10)


def counts(sessions):
    with sessions() as db:
        row = db.get(Season, "villa-1")
        return (
            row.revision,
            row.snapshot,
            db.scalar(select(func.count()).select_from(ShowEventRow)),
            db.scalar(select(func.count()).select_from(RecapRow)),
        )


def test_migration_restart_votes_history_and_replay(storage):
    settings, engine, sessions, show = storage
    user = add_user(sessions)
    goal = show.view()[1].goals[0]
    show.vote(user.id, vote_input(goal, 2))
    with sessions() as db:
        snapshot = SimulationSnapshot.model_validate(db.get(Season, "villa-1").snapshot)
    expected = replay_from(snapshot, [], ticks=1).snapshot().model_dump(mode="json")
    show.tick()
    with sessions() as db:
        assert db.get(Season, "villa-1").snapshot == expected
        assert db.scalar(select(func.count()).select_from(VoteRow)) == 1
    engine.dispose()
    reopened, fresh_sessions = connect(settings.database_url)
    try:
        fresh = ShowService(fresh_sessions, settings)
        assert fresh.view()[0].tick == 1
        assert fresh.history().total == 1
        assert fresh.view()[0].latest_recap.story_goal_id == goal.id
        assert fresh.view("en")[0].latest_recap.locale == "en"
    finally:
        reopened.dispose()


def test_tick_rolls_back_snapshot_journal_and_recap(storage, monkeypatch):
    _, _, sessions, show = storage
    before = counts(sessions)
    original = show._save

    def broken(*args):
        original(*args)
        raise RuntimeError("injected failure after flush")

    monkeypatch.setattr(show, "_save", broken)
    with pytest.raises(RuntimeError):
        show.tick()
    assert counts(sessions) == before


def test_two_workers_cannot_resolve_same_tick(storage):
    _, _, sessions, show = storage
    due(sessions)
    with ThreadPoolExecutor(max_workers=2) as pool:
        completed = list(pool.map(lambda _: run_once(show), range(2)))
    assert sum(completed) == 1
    assert show.view()[0].tick == 1
    assert show.history().total == 1
    assert run_once(show) == 0


def test_stale_revision_is_rejected(storage):
    _, _, _, show = storage
    revision = show.view()[0].revision
    show.tick(expected_revision=revision)
    with pytest.raises(DomainError, match="conflict"):
        show.tick(expected_revision=revision)
    assert show.view()[0].tick == 1


def test_journal_append_only_and_db_budget_constraint(storage):
    _, _, sessions, _ = storage
    with sessions.begin() as db:
        with pytest.raises(IntegrityError, match="append-only"):
            db.execute(text("UPDATE show_events SET kind='recap'"))
    user = add_user(sessions)
    with pytest.raises(IntegrityError):
        with sessions.begin() as db:
            db.add(Budget(season_id="villa-1", user_id=user.id, tick=1, spent=4))


def test_database_budget_concurrent_votes_and_idempotency(storage):
    _, _, sessions, show = storage
    user = add_user(sessions)
    goal = show.view()[1].goals[0]
    vote = vote_input(goal, 2)
    assert show.vote(user.id, vote).remaining == 1
    assert show.vote(user.id, vote).duplicate
    with pytest.raises(DomainError, match="conflict"):
        show.vote(user.id, vote.model_copy(update={"influence_points": 1}))

    def cast(_):
        try:
            show.vote(user.id, vote_input(goal))
            return True
        except DomainError:
            return False

    with ThreadPoolExecutor(max_workers=5) as pool:
        assert sum(pool.map(cast, range(5))) == 1
    assert show.view(user_id=user.id)[1].remaining == 0
    assert show.view()[1].goals[0].votes == 3
    with sessions() as db:
        assert db.scalar(select(func.sum(VoteRow.points))) == 3
    show.tick()
    assert show.view(user_id=user.id)[1].remaining == 3


def test_worker_once_cli(storage):
    _, _, sessions, show = storage
    due(sessions)
    assert main(["--once"]) == 0
    assert show.view()[0].tick == 1
    assert main(["--once"]) == 0
    assert show.view()[0].tick == 1
    assert main(["--init"]) == 0
    assert show.view()[0].tick == 1


def test_html_guest_register_vote_archive_account_logout(client, storage):
    for path in ("/", "/show", "/history", "/login", "/register"):
        assert client.get(path).status_code == 200
    assert client.get("/account").status_code == 401
    assert register(client).status_code == 200
    assert client.get("/account").status_code == 200
    page = client.get("/show").text
    assert 'hx-post="/vote' in page and 'hx-target="#goals"' in page
    csrf_token = token(client)
    goal = client.get("/public/goals").json()[0]
    response = client.post(
        "/vote",
        headers={"HX-Request": "true"},
        data={
            "csrf": csrf_token,
            "story_goal_id": goal["id"],
            "tick": goal["tick"],
            "influence_points": 2,
            "request_id": uuid4().hex,
        },
    )
    assert response.status_code == 200
    assert "Голос принят" in response.text and "<html" not in response.text
    assert client.get("/public/influence").json()["remaining"] == 1
    revision = client.get("/public/season").json()["revision"]
    r = client.post(
        "/public/dev/ticks",
        headers={"x-csrf-token": csrf_token},
        json={"ticks": 1, "expected_revision": revision},
    )
    assert r.status_code == 200 and r.json()["tick"] == 1
    assert "Разговор" in client.get("/history").text
    assert goal["title"] in client.get("/account").text
    old_cookie = client.cookies.get("glasshouse_session")
    assert client.post("/logout", data={"csrf": csrf_token}).status_code == 200
    client.cookies.set("glasshouse_session", old_cookie)
    assert client.get("/public/session").json()["authenticated"] is False
    assert client.get("/account").status_code == 401
    assert (
        client.post(
            "/login",
            data={
                "csrf": token(client),
                "email": "viewer@example.com",
                "password": "A secure test password",
            },
        ).status_code
        == 200
    )
    with storage[2]() as db:
        user = db.scalar(select(User))
        assert user.password_hash.startswith("$argon2id$")
        assert "secure test password" not in user.password_hash


def test_csrf_impersonation_stale_votes_and_input_validation(client):
    assert client.post("/register", data={"email": "x@example.com"}).status_code == 403
    csrf_token = token(client)
    goal = client.get("/public/goals").json()[0]
    payload = {
        "story_goal_id": goal["id"],
        "tick": goal["tick"],
        "influence_points": 1,
        "request_id": uuid4().hex,
    }
    headers = {"x-csrf-token": csrf_token}
    assert client.post("/public/votes", headers=headers, json=payload).status_code == 401
    register(client)
    assert client.post("/public/votes", headers=headers, json=payload).status_code == 403
    headers = {"x-csrf-token": token(client)}
    for change in (
        {"viewer_id": "someone-else"},
        {"influence_points": True},
        {"influence_points": -1},
        {"tick": "1"},
    ):
        assert (
            client.post("/public/votes", headers=headers, json={**payload, **change}).status_code
            == 422
        )
    assert (
        client.post("/public/votes", headers=headers, json={**payload, "tick": 2}).status_code
        == 409
    )
    assert client.get("/public/influence").json()["remaining"] == 3


def test_production_has_no_debug_and_secure_cookie(storage):
    production = replace(storage[0], app_env="production", session_secret="s" * 48)
    with TestClient(create_app(production), base_url="https://testserver") as client:
        response = client.get("/public/session")
        cookie = response.headers["set-cookie"].lower()
        assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie
        for path in ("/public/dev/ticks", "/dev/tick", "/sim/run", "/agents/max", "/events"):
            assert client.post(path, json={}).status_code == 404
        assert client.get("/ready").json() == {"status": "ready"}
        assert client.get("/health").json() == {"status": "ok"}


def test_locales_and_no_private_public_data(client, storage):
    register(client, locale="en")
    assert client.get("/public/season").json()["setting"] == "The Villa"
    assert client.get("/public/goals").json()[0]["title"] == "Time to talk"
    csrf_token = token(client)
    assert (
        client.post(
            "/locale", data={"csrf": csrf_token, "locale": "ru", "next": "/show"}
        ).status_code
        == 200
    )
    assert client.get("/public/season").json()["setting"] == "Вилла"
    storage[3].tick()
    for lang in ("ru", "en"):
        for path in ("season", "goals", "timeline", "recaps", "influence"):
            response = client.get(f"/public/{path}?lang={lang}")
            assert response.status_code == 200
            serialized = response.text
            for private in (
                "password",
                "boundaries",
                "max_unpaid_debt",
                "viewer@example.com",
                "viewer_id",
                "user_id",
                "director_score",
                "raw_prompt",
                "secret_boundary",
            ):
                assert private not in serialized
        assert client.get(f"/public/recaps?lang={lang}").json()["items"][0]["locale"] == lang


def test_pagination_and_health_readiness(client, storage):
    show = storage[3]
    for _ in range(3):
        show.tick()
    first = client.get("/public/recaps?limit=2").json()
    second = client.get("/public/recaps?limit=2&page=2").json()
    assert [r["tick"] for r in first["items"]] == [3, 2]
    assert first["has_next"] and first["total"] == 3
    assert [r["tick"] for r in second["items"]] == [1]
    assert not second["has_next"]
    assert client.get("/public/recaps?limit=0").status_code == 422
    assert client.get("/ready").status_code == 200


def test_login_throttle_shared_between_app_instances(client, storage):
    register(client)
    client.post("/logout", data={"csrf": token(client)})
    for _ in range(8):
        r = client.post(
            "/login",
            data={
                "csrf": token(client),
                "email": "viewer@example.com",
                "password": "wrong-password",
            },
        )
        assert r.status_code == 401
        assert "wrong-password" not in r.text
    with TestClient(create_app(storage[0])) as other:
        r = other.post(
            "/login",
            data={
                "csrf": token(other),
                "email": "viewer@example.com",
                "password": "A secure test password",
            },
        )
        assert r.status_code == 429


def test_validation_rejects_xss_and_never_echoes_password(client):
    r = client.post(
        "/register",
        data={
            "csrf": token(client),
            "email": "invalid",
            "display_name": "<script>alert(1)</script>",
            "password": "super-secret-password",
            "locale": "ru",
        },
    )
    assert r.status_code == 422
    assert "<script>alert" not in r.text and "super-secret-password" not in r.text
    assert client.get("/public/session").json()["authenticated"] is False


def test_logout_requires_post_and_csrf(client):
    register(client)
    assert client.get("/logout").status_code == 405
    assert client.post("/logout").status_code == 403
    assert client.get("/public/session").json()["authenticated"]


def test_openapi_documents_errors_and_vote_contract(client):
    schema = client.get("/openapi.json").json()
    assert "409" in schema["paths"]["/public/votes"]["post"]["responses"]
    assert "viewer_id" not in schema["components"]["schemas"]["VoteInput"]["properties"]
    assert schema["components"]["schemas"]["VoteInput"]["additionalProperties"] is False


def test_body_limit_including_chunked_request(client):
    def chunks():
        yield b"a" * 9000
        yield b"b" * 9000

    assert client.post("/login", content=chunks()).status_code == 413
    assert client.post("/login", content=b"x" * 17000).status_code == 413


def test_narrator_failure_persists_tick_and_safe_audit(storage):
    from glasshouse.live.narrator import OpenRouterNarrator

    settings, _, sessions, show = storage

    def unavailable(**kwargs):
        raise TimeoutError("private provider payload")

    show.narrator = OpenRouterNarrator(
        replace(settings, llm_enabled=True, api_key="secret", narrator_model="configured/model"),
        unavailable,
    )
    assert show.tick()
    assert show.view()[0].latest_recap.narrated is False
    with sessions() as db:
        audit = db.get(LLMRun, ("villa-1", 1))
        assert audit.status == "fallback" and audit.error_type == "TimeoutError"
        assert audit.model_requested == "configured/model"


def test_vote_throttling_and_budget_errors_are_localized(client):
    register(client, locale="en")
    goal = client.get("/public/goals").json()[0]
    payload = {
        "story_goal_id": goal["id"],
        "tick": goal["tick"],
        "influence_points": 3,
        "request_id": uuid4().hex,
    }
    headers = {"x-csrf-token": token(client)}
    assert client.post("/public/votes", headers=headers, json=payload).status_code == 201
    blocked = client.post(
        "/public/votes", headers=headers, json={**payload, "request_id": uuid4().hex}
    )
    assert blocked.status_code == 409 and blocked.json()["code"] == "budget"
    assert "No influence" in blocked.json()["message"]
    for _ in range(18):
        assert client.post("/public/votes", headers=headers, json=payload).status_code == 201
    assert client.post("/public/votes", headers=headers, json=payload).status_code == 429
