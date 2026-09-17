from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import time
from datetime import timedelta
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import case, delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError

from glasshouse.live.models import AuthSession, RateLimit, User, now
from glasshouse.live.schemas import Locale
from glasshouse.live.service import DomainError


class Profile(BaseModel):
    model_config = ConfigDict(extra='forbid')
    display_name: str = Field(min_length=2, max_length=40)
    locale: Locale = 'ru'

    @field_validator('display_name')
    @classmethod
    def valid_name(cls, value):
        value = ' '.join(value.split())
        if len(value) < 2 or not re.fullmatch(r'[\w .\-]{2,40}', value):
            raise ValueError('Invalid name')
        return value


class Registration(Profile):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value):
        return value.lower()


class Login(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)


class AuthService:
    def __init__(self, sessions, secret):
        self.sessions = sessions
        self.secret = secret.encode()
        self.hasher = PasswordHasher()
        self.dummy_hash = self.hasher.hash(secrets.token_urlsafe(32))

    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def limit(self, scope, identity, maximum, seconds):
        # Shared across API processes, atomic on both supported databases.
        key = hmac.new(self.secret, f'{scope}:{identity}'.encode(), hashlib.sha256).hexdigest()
        window = int(time.time()) // seconds * seconds
        with self.sessions.begin() as db:
            insert = sqlite_insert if db.bind.dialect.name == 'sqlite' else pg_insert
            stmt = insert(RateLimit).values(key=key, window=window, attempts=1)
            stmt = stmt.on_conflict_do_update(index_elements=['key'], set_={
                'window': window,
                'attempts': case((RateLimit.window == window, RateLimit.attempts + 1), else_=1),
            }).returning(RateLimit.attempts)
            count = db.scalar(stmt)
        if count > maximum:
            raise DomainError('rate', 429)

    def register(self, data):
        user = User(id=str(uuid4()), email=str(data.email).lower(),
                    display_name=data.display_name, locale=data.locale,
                    password_hash=self.hasher.hash(data.password))
        try:
            with self.sessions.begin() as db:
                db.add(user)
        except IntegrityError:
            raise DomainError('registered', 409) from None
        return user

    def login(self, data):
        with self.sessions.begin() as db:
            user = db.scalar(select(User).where(User.email == str(data.email).lower()))
            try:
                self.hasher.verify(user.password_hash if user else self.dummy_hash, data.password)
            except (VerificationError, InvalidHashError):
                raise DomainError('credentials', 401) from None
            if user is None:
                raise DomainError('credentials', 401)
            if self.hasher.check_needs_rehash(user.password_hash):
                user.password_hash = self.hasher.hash(data.password)
            return user

    def start_session(self, user):
        token = secrets.token_urlsafe(32)
        with self.sessions.begin() as db:
            db.add(AuthSession(token_hash=self.digest(token), user_id=user.id,
                               expires_at=now() + timedelta(days=7)))
        return token

    def current_user(self, token):
        if not token:
            return None
        with self.sessions() as db:
            session = db.get(AuthSession, self.digest(token))
            if not session or session.expires_at <= now():
                return None
            return db.get(User, session.user_id)

    def logout(self, token):
        if token:
            with self.sessions.begin() as db:
                db.execute(delete(AuthSession).where(AuthSession.token_hash == self.digest(token)))

    def profile(self, user_id, data):
        with self.sessions.begin() as db:
            user = db.get(User, user_id)
            if user is None:
                raise DomainError('auth', 401)
            user.display_name = data.display_name
            user.locale = data.locale
