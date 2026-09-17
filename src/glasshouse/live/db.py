from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from glasshouse.live.config import database_url


def connect(url: str):
    options = {'check_same_thread': False, 'timeout': 15} if url.startswith('sqlite') else {}
    engine = create_engine(database_url(url), connect_args=options, pool_pre_ping=True)
    if engine.dialect.name == 'sqlite':
        @event.listens_for(engine, 'connect')
        def sqlite_settings(connection, _):
            cursor = connection.cursor()
            cursor.execute('PRAGMA foreign_keys=ON')
            cursor.execute('PRAGMA journal_mode=WAL')
            cursor.close()
    return engine, sessionmaker(engine, expire_on_commit=False)
