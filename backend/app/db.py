"""Tiger Data (Postgres) connection pool.

enabled() is False when TIGER_DATABASE_URL is empty. Routes then fall back to mock data so the
frontend can build against the API before the database exists.
"""
from contextlib import contextmanager
from typing import Iterator, Optional

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import get_settings

_pool: Optional[ConnectionPool] = None


def enabled() -> bool:
    return bool(get_settings().tiger_database_url)


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            get_settings().tiger_database_url,
            min_size=1,
            max_size=5,
            kwargs={"row_factory": dict_row},
            open=False,
        )
        _pool.open(wait=False)
    return _pool


@contextmanager
def connection() -> Iterator[Connection]:
    """Yields a pooled connection; commits on clean exit, rolls back on error."""
    with _get_pool().connection() as conn:
        yield conn


def close() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
