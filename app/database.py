"""SQLite database connection and schema management."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

_SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS products (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    price_cents INTEGER NOT NULL,
    category    TEXT,
    image_url   TEXT,
    stock       INTEGER NOT NULL DEFAULT 0,
    is_active   INTEGER NOT NULL DEFAULT 1,
    is_featured INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    google_id   TEXT UNIQUE NOT NULL,
    email       TEXT UNIQUE NOT NULL,
    name        TEXT,
    avatar_url  TEXT,
    is_admin    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    user_id     TEXT REFERENCES users(id),
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cart_items (
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    product_id  TEXT NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL DEFAULT 1,
    added_at    TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (session_id, product_id)
);

CREATE TABLE IF NOT EXISTS orders (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL,
    user_id     TEXT REFERENCES users(id),
    status      TEXT NOT NULL DEFAULT 'pending',
    total_cents INTEGER NOT NULL,
    customer_email TEXT NOT NULL,
    customer_name  TEXT,
    shipping_address TEXT,
    notes       TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS order_items (
    order_id    TEXT NOT NULL REFERENCES orders(id),
    product_id  TEXT NOT NULL,
    product_name TEXT NOT NULL,
    price_cents INTEGER NOT NULL,
    quantity    INTEGER NOT NULL,
    PRIMARY KEY (order_id, product_id)
);
"""

# Module-level database path — set during app startup via init_db()
_db_path: str = ""


def init_db(path: str) -> None:
    """Initialize the database: create file, enable WAL, create schema tables."""
    global _db_path  # noqa: PLW0603
    _db_path = path

    # Ensure parent directory exists
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite connection with WAL mode and foreign keys enabled.

    Commits on success, rolls back on exception.
    """
    conn = sqlite3.connect(_db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
