"""Synchronous PostgreSQL helpers (API + Celery worker)."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from psycopg2.extensions import connection as PgConnection

from app.core.config import get_settings

psycopg2.extras.register_uuid()


def get_dsn() -> str:
    return get_settings().database_url_sync


@contextmanager
def get_connection() -> Generator[PgConnection, None, None]:
    conn = psycopg2.connect(get_dsn())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def get_cursor(*, dict_cursor: bool = True) -> Generator:
    factory = psycopg2.extras.RealDictCursor if dict_cursor else None
    with get_connection() as conn:
        with conn.cursor(cursor_factory=factory) as cur:
            yield cur
