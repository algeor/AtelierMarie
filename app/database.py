"""Postgres connection layer.

Schema is owned entirely by Alembic (design Decision 3); this module no longer
creates tables, seeds rows, or runs startup backfills. It provides:

- a module-global psycopg ``ConnectionPool`` (Decision 2a) — mirroring the old
  ``_db_path`` global so ``get_db()`` stays the single chokepoint and the
  connection-taking service signatures are untouched;
- ``get_db()`` — a context manager yielding a pooled connection, commit on
  success / rollback on error;
- ``init_db(url)`` — open the pool and fail startup if the connected database is
  behind the Alembic head revision (Decision 3);
- small SQL/row helpers for the psycopg idioms callers need (Decisions 2, 3.4);
- ``cleanup_expired_sessions()`` — the one background sweep that lived here.

The pool's ``configure=`` callback is the single place every pooled connection
gets ``row_factory=dict_row`` (keyed row access, Decision 3.3) and
``TimeZone=UTC`` (Decision 12) set exactly once.
"""

from collections.abc import Generator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import psycopg
import structlog
from psycopg import Connection
from psycopg.rows import DictRow, dict_row
from psycopg_pool import ConnectionPool

logger = structlog.get_logger(__name__)

# psycopg exception aliases so callers can catch database errors without
# importing psycopg directly (Decision 5 / task 3.5). ``IntegrityError`` covers
# constraint violations (unique, FK, check, not-null); ``DatabaseError`` is the
# broad base for connection/operational failures exposed to callers.
IntegrityError = psycopg.errors.IntegrityError
DatabaseError = psycopg.errors.DatabaseError
Error = psycopg.Error

# Module-global connection pool — set during app startup via init_db(), mirroring
# the old _db_path global. None until init_db() runs. Under pytest-xdist each
# worker is a separate process with its own per-process pool (Decision 2a).
DbConnection = Connection[DictRow]
DbRow = DictRow

_pool: ConnectionPool[DbConnection] | None = None


def _configure_connection(conn: DbConnection) -> None:
    """Configure every pooled connection exactly once (Decisions 2a, 3.3, 12).

    - ``row_factory = dict_row`` gives keyed (dict-like) row access, so the
      ~479 service functions that read ``row["column"]`` keep working.
    - ``TimeZone = UTC`` guarantees any text->timestamptz cast on a surviving
      string-param site resolves in UTC (Decision 12 guardrail).
    """
    conn.row_factory = dict_row
    with conn.cursor() as cur:
        cur.execute("SET TIME ZONE 'UTC'")
    conn.commit()


def _script_head_revisions() -> set[str]:
    """Return the Alembic script directory's head revision id(s)."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    alembic_ini = Path(__file__).resolve().parent.parent / "alembic.ini"
    config = Config(str(alembic_ini))
    script = ScriptDirectory.from_config(config)
    return set(script.get_heads())


def _db_current_revisions(conn: DbConnection) -> set[str]:
    """Return the revision id(s) recorded in the database's alembic_version table.

    An empty set means the database has never been stamped (no migrations
    applied). Any read failure is treated as "no revision recorded".
    """
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT version_num FROM alembic_version")
            return {row["version_num"] for row in cur.fetchall()}
    except psycopg.Error:
        return set()


def _verify_migration_head(conn: DbConnection) -> None:
    """Fail startup unless the database is at the Alembic head revision.

    Compares the database's current revision(s) against the script directory's
    head(s) (Decision 3). Startup must fail with a clear error if migrations
    have not been applied or the database has diverged; Alembic — not app
    startup — owns applying schema.
    """
    heads = _script_head_revisions()
    current = _db_current_revisions(conn)
    if current != heads:
        msg = (
            "Database is not at the Alembic head revision. "
            f"Database revision(s): {sorted(current) or '<none applied>'}; "
            f"script head(s): {sorted(heads)}. "
            "Run `alembic upgrade head` before starting the app."
        )
        raise RuntimeError(msg)


def init_db(
    url: str,
    *,
    min_size: int = 2,
    max_size: int = 20,
    timeout: float = 8.0,
) -> None:
    """Open the connection pool and verify the DB is at the Alembic head.

    Replaces the former startup schema-creation path: schema now comes only from
    ``alembic upgrade head``. This opens a module-global pool against ``url``,
    then fails fast if the connected database is behind head (Decision 3).

    Pool sizing (Decision 14) is passed in from the app lifespan so it stays a
    ``config.py`` setting; the defaults here mirror the production seed and keep
    per-worker test pools small. ``timeout`` is the pool-wait ceiling: under burst
    a caller waits up to this long for a free connection, then raises rather than
    hanging (bursts queue then fail clean).
    """
    global _pool  # noqa: PLW0603

    if _pool is not None:
        _pool.close()

    _pool = ConnectionPool(
        conninfo=url,
        # A single request can hold one connection and, within that scope, call
        # a service that opens its own get_db() (e.g. checkout -> pricing /
        # delivery_settings_service). psycopg defaults max_size to min_size, so a
        # size-1 pool dead-locks on the nested acquire. max_size carries headroom
        # for the deepest nesting plus concurrent requests.
        min_size=min_size,
        max_size=max_size,
        timeout=timeout,
        open=True,
        configure=_configure_connection,
        kwargs={"autocommit": False},
    )
    _pool.wait()

    with _pool.connection() as conn:
        _verify_migration_head(conn)


def close_db() -> None:
    """Close the connection pool. Called from the app lifespan on shutdown."""
    global _pool  # noqa: PLW0603
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def get_db() -> Generator[DbConnection, None, None]:
    """Yield a pooled psycopg connection.

    Commits on success, rolls back on exception. The connection is returned to
    the pool automatically. Row factory (dict_row) and TimeZone=UTC are set once
    per connection by the pool's configure callback, so callers need no
    per-request setup. This is the single connection chokepoint: service
    signatures that take a ``conn`` are unchanged.
    """
    if _pool is None:
        msg = "Database pool is not initialized. Call init_db() first."
        raise RuntimeError(msg)

    with _pool.connection() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


# ---------------------------------------------------------------------------
# Shared SQL / row helpers (Decisions 2, 3.3, 3.4)
# ---------------------------------------------------------------------------


def row_get(row: dict[str, Any], key: str, default: Any = None) -> Any:
    """Return ``row[key]`` if present and non-None, else ``default``.

    dict_row rows are plain dicts, so keyed access already works; this keeps a
    defensive accessor for service transformations that must tolerate an absent
    or NULL column.
    """
    value = row.get(key)
    return value if value is not None else default


def require_row(row: DbRow | None, message: str = "Expected database row") -> DbRow:
    """Return a fetched row, or fail explicitly when an invariant query returned none."""
    if row is None:
        raise RuntimeError(message)
    return row


def row_to_dict(row: dict[str, Any], defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    """Copy a dict_row row to a plain dict, substituting defaults for None values."""
    result = dict(row)
    if defaults:
        for key, default_value in defaults.items():
            if key in result and result[key] is None:
                result[key] = default_value
    return result


def any_param(values: Sequence[Any]) -> list[Any]:
    """Return a list suitable for a ``= ANY(%s)`` array parameter.

    psycopg adapts a Python list to a Postgres array, so a dynamic membership
    test binds a single parameter instead of building N ``?`` placeholders::

        cur.execute("SELECT * FROM products WHERE id = ANY(%s)", (any_param(ids),))
    """
    return list(values)


def insert_returning_id(
    conn: DbConnection,
    sql: str,
    params: Sequence[Any] = (),
) -> Any:
    """Execute an INSERT that ends in ``RETURNING id`` and return the new id.

    Postgres identity columns surface generated ids via a ``RETURNING`` clause. The
    caller is responsible for including ``RETURNING id`` in ``sql``.
    """
    with conn.cursor() as cur:
        cur.execute(sql, params)
        result = cur.fetchone()
    if result is None:
        msg = "INSERT ... RETURNING id produced no row"
        raise RuntimeError(msg)
    return result["id"]


def cleanup_expired_sessions() -> int:
    """Delete expired sessions and return count of removed rows.

    expires_at is a timestamptz; comparison against CURRENT_TIMESTAMP is a native
    instant comparison in Postgres.
    """
    with get_db() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM sessions WHERE expires_at < CURRENT_TIMESTAMP")
        return cur.rowcount
