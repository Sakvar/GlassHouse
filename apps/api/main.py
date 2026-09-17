from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool
from starlette.middleware.sessions import SessionMiddleware

from apps.api.body_limit import BodyLimitMiddleware
from glasshouse.live.auth import AuthService, Login, Profile, Registration
from glasshouse.live.config import Settings
from glasshouse.live.db import connect
from glasshouse.live.i18n import CATEGORIES, ERRORS, STRINGS, TITLES
from glasshouse.live.models import Season, VoteRow
from glasshouse.live.schemas import (
    Error,
    Goal,
    GoalsView,
    Health,
    Locale,
    Page,
    SeasonView,
    SessionView,
    TickInput,
    VoteInput,
    VoteReceipt,
)
from glasshouse.live.service import DomainError, ShowService

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=ROOT / "templates")
ERROR_RESPONSES = {code: {"model": Error} for code in (401, 403, 404, 409, 422, 429, 503)}


def locale_for(request):
    locale = request.query_params.get("lang") or request.session.get("locale", "ru")
    return locale if locale in ("ru", "en") else "ru"


def current_user(request: Request):
    return request.app.state.auth.current_user(request.session.get("token"))


def require_user(request: Request):
    user = current_user(request)
    if not user:
        raise DomainError("auth", 401)
    return user


async def csrf(request: Request):
    supplied = request.headers.get("x-csrf-token", "")
    if not supplied and "application/x-www-form-urlencoded" in request.headers.get(
        "content-type", ""
    ):
        supplied = (await request.form()).get("csrf", "")
    expected = request.session.get("csrf", "")
    if (
        not expected
        or not isinstance(supplied, str)
        or not secrets.compare_digest(supplied, expected)
    ):
        raise DomainError("csrf", 403)


def render(request, template, **context):
    locale = locale_for(request)
    request.session.setdefault("csrf", secrets.token_urlsafe(32))
    user = current_user(request)
    return TEMPLATES.TemplateResponse(
        request=request,
        name=template,
        context={
            "t": STRINGS[locale],
            "locale": locale,
            "user": user,
            "csrf": request.session["csrf"],
            "uuid": lambda: uuid4().hex,
            "development": request.app.state.settings.app_env == "development",
            **context,
        },
    )


def show_context(request):
    user = current_user(request)
    service = request.app.state.show
    season, goals = service.view(locale_for(request), user.id if user else None)
    return {
        "season": season,
        "goals": goals,
        "history": service.history(locale_for(request), limit=3),
    }


def create_app(settings=None):
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        engine, sessions = connect(settings.database_url)
        app.state.engine = engine
        app.state.sessions = sessions
        app.state.show = ShowService(sessions, settings)
        app.state.auth = AuthService(sessions, settings.session_secret)
        app.state.settings = settings
        try:
            # Migrations are a deployment step, never run concurrently by API processes.
            await run_in_threadpool(app.state.show.ensure_season)
            yield
        finally:
            engine.dispose()

    app = FastAPI(
        title="GlassHouse Live", version="0.2.0", lifespan=lifespan, responses=ERROR_RESPONSES
    )
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie="glasshouse_session",
        max_age=7 * 86400,
        same_site="lax",
        https_only=settings.app_env == "production",
    )
    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

    @app.middleware("http")
    async def security_headers(request, call_next):
        length = request.headers.get("content-length", "0")
        if not length.isdigit() or int(length) > 16384:
            return JSONResponse(
                {"code": "invalid", "message": "Request too large"}, status_code=413
            )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        if request.url.path not in ("/docs", "/redoc"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
                "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
                "form-action 'self'"
            )
        if settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.exception_handler(DomainError)
    async def domain_error(request, exc):
        locale = locale_for(request)
        message = ERRORS.get(exc.code, ERRORS["invalid"])[0 if locale == "ru" else 1]
        if request.url.path.startswith("/public/") or request.url.path in ("/ready", "/health"):
            return JSONResponse({"code": exc.code, "message": message}, status_code=exc.status)
        if request.headers.get("HX-Request") == "true" and request.url.path == "/vote":
            response = await run_in_threadpool(
                lambda: render(request, "goals.html", **show_context(request), error=message)
            )
        else:
            response = await run_in_threadpool(lambda: render(request, "error.html", error=message))
        response.status_code = exc.status
        return response

    @app.exception_handler(RequestValidationError)
    @app.exception_handler(ValidationError)
    async def invalid_input(request, exc):
        # Pydantic's default error response may echo passwords or arbitrary input.
        return await domain_error(request, DomainError("invalid", 422))

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):
        logger.error("database_failure error_type=%s", type(exc).__name__)
        message = ERRORS["unavailable"][0 if locale_for(request) == "ru" else 1]
        return JSONResponse({"code": "unavailable", "message": message}, status_code=503)

    @app.get("/health", response_model=Health)
    def health():
        return Health(status="ok")

    @app.get("/ready", response_model=Health)
    def ready(request: Request):
        with request.app.state.sessions() as db:
            version = db.scalar(text("SELECT version_num FROM alembic_version"))
            if version != "002" or not db.get(Season, "villa-1"):
                raise DomainError("unavailable", 503)
        return Health(status="ready")

    @app.get("/public/season", response_model=SeasonView)
    def season(request: Request, lang: Locale | None = None):
        return request.app.state.show.view(locale_for(request))[0]

    @app.get("/public/goals", response_model=list[Goal])
    def goals(request: Request, lang: Locale | None = None):
        return request.app.state.show.view(locale_for(request))[1].goals

    @app.get("/public/influence", response_model=GoalsView)
    def influence(request: Request, lang: Locale | None = None):
        user = current_user(request)
        return request.app.state.show.view(locale_for(request), user.id if user else None)[1]

    @app.get("/public/timeline", response_model=Page)
    @app.get("/public/recaps", response_model=Page)
    def timeline(
        request: Request,
        page: int = Query(1, ge=1),
        limit: int = Query(10, ge=1, le=100),
        from_tick: int = Query(0, ge=0),
        lang: Locale | None = None,
    ):
        return request.app.state.show.history(locale_for(request), page, limit, from_tick)

    @app.get("/public/session", response_model=SessionView)
    def session_token(request: Request):
        request.session.setdefault("csrf", secrets.token_urlsafe(32))
        return {"csrf_token": request.session["csrf"], "authenticated": bool(current_user(request))}

    @app.post(
        "/public/votes", response_model=VoteReceipt, status_code=201, dependencies=[Depends(csrf)]
    )
    def vote(request: Request, body: VoteInput, user=Depends(require_user)):
        request.app.state.auth.limit("votes", user.id, 20, 60)
        return request.app.state.show.vote(user.id, body)

    if settings.app_env == "development":

        @app.post("/public/dev/ticks", response_model=SeasonView, dependencies=[Depends(csrf)])
        def ticks(request: Request, body: TickInput, user=Depends(require_user)):
            request.app.state.auth.limit("ticks", user.id, 10, 60)
            revision = body.expected_revision
            for _ in range(body.ticks):
                request.app.state.show.tick(expected_revision=revision)
                revision += 1
            return request.app.state.show.view(locale_for(request))[0]

        @app.post("/dev/tick", dependencies=[Depends(csrf)])
        async def html_tick(request: Request, user=Depends(require_user)):
            form = await request.form()
            try:
                revision = int(form["revision"])
            except (KeyError, ValueError):
                raise DomainError("invalid", 422) from None
            await run_in_threadpool(request.app.state.auth.limit, "ticks", user.id, 10, 60)
            await run_in_threadpool(request.app.state.show.tick, expected_revision=revision)
            return RedirectResponse("/show", status_code=303)

    @app.get("/", response_class=HTMLResponse)
    def landing(request: Request):
        return render(request, "landing.html", **show_context(request))

    @app.get("/show", response_class=HTMLResponse)
    def show(request: Request):
        return render(request, "show.html", **show_context(request))

    @app.get("/fragments/live", response_class=HTMLResponse)
    def live_fragment(request: Request):
        return render(request, "live.html", **show_context(request))

    @app.get("/history", response_class=HTMLResponse)
    def history(request: Request, page: int = Query(1, ge=1)):
        return render(
            request,
            "history.html",
            history=request.app.state.show.history(locale_for(request), page=page),
        )

    @app.get("/login", response_class=HTMLResponse)
    @app.get("/register", response_class=HTMLResponse)
    def auth_form(request: Request):
        return render(request, "auth.html", registering=request.url.path == "/register")

    async def authenticate(request, registering):
        form = await request.form()
        auth = request.app.state.auth
        ip = request.client.host if request.client else "unknown"
        await run_in_threadpool(
            auth.limit,
            "register-ip" if registering else "login-ip",
            ip,
            10 if registering else 30,
            3600 if registering else 300,
        )
        data = {k: v for k, v in form.items() if k != "csrf"}
        parsed = Registration.model_validate(data) if registering else Login.model_validate(data)
        if not registering:
            await run_in_threadpool(auth.limit, "login-account", str(parsed.email).lower(), 8, 300)
        user = await run_in_threadpool(auth.register if registering else auth.login, parsed)
        await run_in_threadpool(auth.logout, request.session.get("token"))
        token = await run_in_threadpool(auth.start_session, user)
        request.session.clear()
        request.session.update(token=token, csrf=secrets.token_urlsafe(32), locale=user.locale)
        return RedirectResponse("/show", status_code=303)

    @app.post("/register", dependencies=[Depends(csrf)])
    async def register(request: Request):
        return await authenticate(request, True)

    @app.post("/login", dependencies=[Depends(csrf)])
    async def login(request: Request):
        return await authenticate(request, False)

    @app.post("/logout", dependencies=[Depends(csrf)])
    def logout(request: Request):
        request.app.state.auth.logout(request.session.get("token"))
        locale = locale_for(request)
        request.session.clear()
        request.session["locale"] = locale
        return RedirectResponse("/", status_code=303)

    @app.post("/locale", dependencies=[Depends(csrf)])
    async def change_locale(request: Request):
        form = await request.form()
        locale = form.get("locale")
        if locale not in ("ru", "en"):
            raise DomainError("invalid", 422)
        user = await run_in_threadpool(current_user, request)
        if user:
            await run_in_threadpool(
                request.app.state.auth.profile,
                user.id,
                Profile(display_name=user.display_name, locale=locale),
            )
        request.session["locale"] = locale
        destination = form.get("next", "/show")
        if destination not in ("/", "/show", "/history", "/account", "/login", "/register"):
            destination = "/show"
        return RedirectResponse(destination, status_code=303)

    @app.get("/account", response_class=HTMLResponse)
    def account(request: Request, user=Depends(require_user)):
        with request.app.state.sessions() as db:
            votes = db.scalars(
                select(VoteRow)
                .where(VoteRow.user_id == user.id)
                .order_by(VoteRow.created_at.desc())
                .limit(30)
            ).all()
            locale = locale_for(request)
            history = [
                {
                    "tick": v.tick,
                    "points": v.points,
                    "title": TITLES[locale][CATEGORIES.index(v.goal_id.split(":")[-1])],
                }
                for v in votes
            ]
        return render(request, "account.html", votes=history)

    @app.post("/account", dependencies=[Depends(csrf)])
    async def update_account(request: Request, user=Depends(require_user)):
        form = await request.form()
        data = Profile.model_validate({k: v for k, v in form.items() if k != "csrf"})
        await run_in_threadpool(request.app.state.auth.profile, user.id, data)
        request.session["locale"] = data.locale
        return RedirectResponse("/account", status_code=303)

    @app.post("/vote", response_class=HTMLResponse, dependencies=[Depends(csrf)])
    async def html_vote(request: Request, user=Depends(require_user)):
        form = await request.form()
        try:
            vote = VoteInput(
                story_goal_id=form["story_goal_id"],
                tick=int(form["tick"]),
                influence_points=int(form["influence_points"]),
                request_id=form["request_id"],
            )
        except (KeyError, ValueError):
            raise DomainError("invalid", 422) from None
        await run_in_threadpool(request.app.state.auth.limit, "votes", user.id, 20, 60)
        await run_in_threadpool(request.app.state.show.vote, user.id, vote)
        if request.headers.get("HX-Request") == "true":
            return await run_in_threadpool(
                lambda: render(
                    request,
                    "goals.html",
                    **show_context(request),
                    notice=STRINGS[locale_for(request)]["voted"],
                )
            )
        return RedirectResponse("/show", status_code=303)

    return app


app = create_app()
