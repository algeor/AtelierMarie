"""SQLite database connection and schema management."""

import os
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

_SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS products (
    id          TEXT PRIMARY KEY,
    name_en     TEXT NOT NULL,
    name_bg     TEXT,
    description_en TEXT,
    description_bg TEXT,
    materials   TEXT,
    days_to_craft INTEGER,
    price_cents INTEGER NOT NULL CHECK (price_cents > 0),
    category    TEXT,
    image_url   TEXT,
    stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    is_active   INTEGER NOT NULL DEFAULT 1,
    is_featured INTEGER NOT NULL DEFAULT 0,
    translation_stale_bg INTEGER NOT NULL DEFAULT 0,
    translation_stale_en INTEGER NOT NULL DEFAULT 0,
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
    preferred_locale TEXT NOT NULL DEFAULT 'en',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

CREATE TABLE IF NOT EXISTS cart_items (
    session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    product_id  TEXT NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 1 AND quantity <= 99),
    added_at    TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (session_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_cart_items_session_id ON cart_items(session_id);

CREATE TABLE IF NOT EXISTS orders (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL,
    user_id     TEXT REFERENCES users(id),
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')),
    total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
    customer_email TEXT NOT NULL,
    customer_name  TEXT,
    shipping_address TEXT,
    notes       TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_orders_session_id ON orders(session_id);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

-- Order items: snapshot at purchase time.
-- product_id is intentionally NOT a foreign key — these are immutable records
-- that must survive even if the original product is removed.
CREATE TABLE IF NOT EXISTS order_items (
    order_id    TEXT NOT NULL REFERENCES orders(id),
    product_id  TEXT NOT NULL,
    product_name TEXT NOT NULL,
    price_cents INTEGER NOT NULL CHECK (price_cents > 0),
    quantity    INTEGER NOT NULL CHECK (quantity >= 1 AND quantity <= 99),
    PRIMARY KEY (order_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_is_active ON products(is_active);

-- Reactions: session-scoped emoji reactions per product (Layer 1 — social proof)
CREATE TABLE IF NOT EXISTS reactions (
    session_id     TEXT NOT NULL,
    product_id     TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    reaction_type  TEXT NOT NULL CHECK (reaction_type IN ('heart', 'thumbs_up')),
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (session_id, product_id, reaction_type)
);

CREATE INDEX IF NOT EXISTS idx_reactions_product_type ON reactions(product_id, reaction_type);
CREATE INDEX IF NOT EXISTS idx_reactions_session_created ON reactions(session_id, created_at);

-- Reaction toggle log: append-only rate-limit tracking (toggles remove from reactions table)
CREATE TABLE IF NOT EXISTS reaction_toggle_log (
    session_id  TEXT NOT NULL,
    product_id  TEXT NOT NULL,
    toggled_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_reaction_toggle_log_session_time
    ON reaction_toggle_log(session_id, toggled_at);

-- Comments: lightweight per-product comment thread (Layer 1 — social proof)
CREATE TABLE IF NOT EXISTS comments (
    id          TEXT PRIMARY KEY,
    product_id  TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    session_id  TEXT NOT NULL,
    user_id     TEXT REFERENCES users(id) ON DELETE SET NULL,
    display_name TEXT NOT NULL,
    body        TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_comments_product_created ON comments(product_id, created_at);
CREATE INDEX IF NOT EXISTS idx_comments_session_created ON comments(session_id, created_at);

-- Auto-update updated_at on row modification
CREATE TRIGGER IF NOT EXISTS products_updated_at AFTER UPDATE ON products
BEGIN
    UPDATE products SET updated_at = datetime('now') WHERE rowid = NEW.rowid;
END;

CREATE TRIGGER IF NOT EXISTS orders_updated_at AFTER UPDATE ON orders
BEGIN
    UPDATE orders SET updated_at = datetime('now') WHERE rowid = NEW.rowid;
END;

-- Full-text search for products — English index (content-backed via triggers)
CREATE VIRTUAL TABLE IF NOT EXISTS products_fts_en USING fts5(
    name_en,
    description_en,
    category,
    content='products',
    content_rowid='rowid'
);

-- Full-text search for products — Bulgarian index (content-backed via triggers)
CREATE VIRTUAL TABLE IF NOT EXISTS products_fts_bg USING fts5(
    name_bg,
    description_bg,
    category,
    content='products',
    content_rowid='rowid'
);

-- Sync triggers: keep English FTS index in sync with products table
CREATE TRIGGER IF NOT EXISTS products_fts_en_insert AFTER INSERT ON products
BEGIN
    INSERT INTO products_fts_en(rowid, name_en, description_en, category)
    VALUES (NEW.rowid, NEW.name_en, COALESCE(NEW.description_en, ''), COALESCE(NEW.category, ''));
END;

CREATE TRIGGER IF NOT EXISTS products_fts_en_delete BEFORE DELETE ON products
BEGIN
    INSERT INTO products_fts_en(products_fts_en, rowid, name_en, description_en, category)
    VALUES ('delete', OLD.rowid, OLD.name_en,
            COALESCE(OLD.description_en, ''), COALESCE(OLD.category, ''));
END;

CREATE TRIGGER IF NOT EXISTS products_fts_en_update AFTER UPDATE ON products
BEGIN
    INSERT INTO products_fts_en(products_fts_en, rowid, name_en, description_en, category)
    VALUES ('delete', OLD.rowid, OLD.name_en,
            COALESCE(OLD.description_en, ''), COALESCE(OLD.category, ''));
    INSERT INTO products_fts_en(rowid, name_en, description_en, category)
    VALUES (NEW.rowid, NEW.name_en, COALESCE(NEW.description_en, ''), COALESCE(NEW.category, ''));
END;

-- Sync triggers: keep Bulgarian FTS index in sync with products table
CREATE TRIGGER IF NOT EXISTS products_fts_bg_insert AFTER INSERT ON products
BEGIN
    INSERT INTO products_fts_bg(rowid, name_bg, description_bg, category)
    VALUES (NEW.rowid, COALESCE(NEW.name_bg, ''),
            COALESCE(NEW.description_bg, ''), COALESCE(NEW.category, ''));
END;

CREATE TRIGGER IF NOT EXISTS products_fts_bg_delete BEFORE DELETE ON products
BEGIN
    INSERT INTO products_fts_bg(products_fts_bg, rowid, name_bg, description_bg, category)
    VALUES ('delete', OLD.rowid, COALESCE(OLD.name_bg, ''),
            COALESCE(OLD.description_bg, ''), COALESCE(OLD.category, ''));
END;

CREATE TRIGGER IF NOT EXISTS products_fts_bg_update AFTER UPDATE ON products
BEGIN
    INSERT INTO products_fts_bg(products_fts_bg, rowid, name_bg, description_bg, category)
    VALUES ('delete', OLD.rowid, COALESCE(OLD.name_bg, ''),
            COALESCE(OLD.description_bg, ''), COALESCE(OLD.category, ''));
    INSERT INTO products_fts_bg(rowid, name_bg, description_bg, category)
    VALUES (NEW.rowid, COALESCE(NEW.name_bg, ''),
            COALESCE(NEW.description_bg, ''), COALESCE(NEW.category, ''));
END;
"""

_PRODUCTS_TABLE_SQL = """\
CREATE TABLE products_new (
    id          TEXT PRIMARY KEY,
    name_en     TEXT NOT NULL,
    name_bg     TEXT,
    description_en TEXT,
    description_bg TEXT,
    materials   TEXT,
    days_to_craft INTEGER,
    price_cents INTEGER NOT NULL CHECK (price_cents > 0),
    category    TEXT,
    image_url   TEXT,
    stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    is_active   INTEGER NOT NULL DEFAULT 1,
    is_featured INTEGER NOT NULL DEFAULT 0,
    translation_stale_bg INTEGER NOT NULL DEFAULT 0,
    translation_stale_en INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

_PRODUCT_COLUMNS = (
    "id",
    "name_en",
    "name_bg",
    "description_en",
    "description_bg",
    "materials",
    "days_to_craft",
    "price_cents",
    "category",
    "image_url",
    "stock",
    "is_active",
    "is_featured",
    "translation_stale_bg",
    "translation_stale_en",
    "created_at",
    "updated_at",
)

_PRODUCT_FTS_RESET_SQL = """\
DROP TRIGGER IF EXISTS products_fts_insert;
DROP TRIGGER IF EXISTS products_fts_delete;
DROP TRIGGER IF EXISTS products_fts_update;
DROP TRIGGER IF EXISTS products_fts_en_insert;
DROP TRIGGER IF EXISTS products_fts_en_delete;
DROP TRIGGER IF EXISTS products_fts_en_update;
DROP TRIGGER IF EXISTS products_fts_bg_insert;
DROP TRIGGER IF EXISTS products_fts_bg_delete;
DROP TRIGGER IF EXISTS products_fts_bg_update;
DROP TABLE IF EXISTS products_fts;
DROP TABLE IF EXISTS products_fts_en;
DROP TABLE IF EXISTS products_fts_bg;
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
        _migrate_existing_schema(conn)
        conn.executescript(_SCHEMA_SQL)
        _rebuild_product_fts(conn)
        conn.commit()
    finally:
        conn.close()

    # Restrict DB file permissions (owner read/write only)
    os.chmod(path, 0o600)


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()  # noqa: S608
    return {str(row[1]) for row in rows}


def _column_expr(columns: set[str], name: str, default: str = "NULL") -> str:
    return f'"{name}"' if name in columns else default


def _add_column_if_missing(
    conn: sqlite3.Connection,
    table: str,
    columns: set[str],
    column: str,
    definition: str,
) -> None:
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")  # noqa: S608
        columns.add(column)


def _migrate_existing_schema(conn: sqlite3.Connection) -> None:
    """Bring pre-bilingual SQLite files up to the current schema."""
    conn.executescript(_PRODUCT_FTS_RESET_SQL)

    if _table_exists(conn, "products"):
        _migrate_products_table(conn)

    if _table_exists(conn, "sessions"):
        session_columns = _table_columns(conn, "sessions")
        _add_column_if_missing(
            conn,
            "sessions",
            session_columns,
            "preferred_locale",
            "preferred_locale TEXT NOT NULL DEFAULT 'en'",
        )


def _migrate_products_table(conn: sqlite3.Connection) -> None:
    columns = _table_columns(conn, "products")
    if columns == set(_PRODUCT_COLUMNS):
        return

    name_en_expr = _column_expr(columns, "name_en", _column_expr(columns, "name", "''"))
    if "name_en" in columns and "name" in columns:
        name_en_expr = "COALESCE(NULLIF(name_en, ''), name)"

    description_en_expr = _column_expr(
        columns,
        "description_en",
        _column_expr(columns, "description"),
    )
    if "description_en" in columns and "description" in columns:
        description_en_expr = "COALESCE(description_en, description)"

    price_expr = _column_expr(columns, "price_cents")
    if "price_cents" not in columns and "price" in columns:
        price_expr = "CAST(ROUND(price * 100) AS INTEGER)"

    select_exprs = [
        _column_expr(columns, "id"),
        name_en_expr,
        _column_expr(columns, "name_bg"),
        description_en_expr,
        _column_expr(columns, "description_bg"),
        _column_expr(columns, "materials"),
        _column_expr(columns, "days_to_craft"),
        price_expr,
        _column_expr(columns, "category"),
        _column_expr(columns, "image_url"),
        _column_expr(columns, "stock", "0"),
        _column_expr(columns, "is_active", "1"),
        _column_expr(columns, "is_featured", "0"),
        _column_expr(columns, "translation_stale_bg", "0"),
        _column_expr(columns, "translation_stale_en", "0"),
        _column_expr(columns, "created_at", "datetime('now')"),
        _column_expr(columns, "updated_at", "datetime('now')"),
    ]

    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        conn.executescript(_PRODUCTS_TABLE_SQL)
        conn.execute(
            f"""
            INSERT INTO products_new ({", ".join(_PRODUCT_COLUMNS)})
            SELECT {", ".join(select_exprs)} FROM products
            """
        )
        conn.execute("DROP TABLE products")
        conn.execute("ALTER TABLE products_new RENAME TO products")
    finally:
        conn.execute("PRAGMA foreign_keys=ON")


def _rebuild_product_fts(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "products"):
        return
    conn.execute("INSERT INTO products_fts_en(products_fts_en) VALUES ('rebuild')")
    conn.execute("INSERT INTO products_fts_bg(products_fts_bg) VALUES ('rebuild')")


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite connection with foreign keys enabled.

    WAL mode is persistent per DB file (set once in init_db), so only
    foreign_keys needs per-connection activation.
    Commits on success, rolls back on exception.
    """
    conn = sqlite3.connect(_db_path)
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


def cleanup_expired_sessions() -> int:
    """Delete expired sessions and return count of removed rows.

    Since expires_at is stored as 'YYYY-MM-DD HH:MM:SS' (UTC), direct
    string comparison with datetime('now') works correctly in SQLite.
    """
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM sessions WHERE expires_at < datetime('now')")
        return cursor.rowcount
