from __future__ import annotations

import argparse
import logging
import signal
import threading
import time

from sqlalchemy import delete

from glasshouse.live.config import Settings
from glasshouse.live.db import connect
from glasshouse.live.models import AuthSession, RateLimit, now
from glasshouse.live.service import DomainError, ShowService

logger = logging.getLogger(__name__)


def run_once(service):
    completed = 0
    for season_id, revision in service.due():
        try:
            completed += service.tick(season_id, expected_revision=revision, due_only=True)
        except DomainError as exc:
            if exc.code != 'conflict':
                raise
    with service.sessions.begin() as db:
        db.execute(delete(AuthSession).where(AuthSession.expires_at <= now()))
        db.execute(delete(RateLimit).where(RateLimit.window < int(time.time()) - 3600))
    return completed


def main(argv=None):
    parser = argparse.ArgumentParser(description='GlassHouse Live worker')
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--init', action='store_true', help='Idempotently create the first season')
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    settings = Settings.from_env()
    engine, sessions = connect(settings.database_url)
    service = ShowService(sessions, settings)
    try:
        if args.init:
            service.ensure_season()
            return 0
        if args.once:
            logger.info('worker_once completed=%s', run_once(service))
            return 0
        stopping = threading.Event()
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: stopping.set())
        while not stopping.is_set():
            try:
                run_once(service)
            except Exception as exc:
                logger.error('worker_failure error_type=%s', type(exc).__name__)
            stopping.wait(settings.poll_seconds)
    finally:
        engine.dispose()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
