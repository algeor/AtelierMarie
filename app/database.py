"""SQLite database connection and schema management."""

import os
import sqlite3
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from app.utils.slugify import slugify, unique_slug

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
    -- Legacy free-text category. Superseded by managed taxonomy (product_type_slug,
    -- category_slug, product_label_assignments). Kept for migration compatibility.
    category    TEXT,
    -- Managed taxonomy references (dynamic-categories). Slugs, not display names.
    product_type_slug TEXT NOT NULL DEFAULT 'candles',
    category_slug     TEXT,
    stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    is_active   INTEGER NOT NULL DEFAULT 1,
    is_featured INTEGER NOT NULL DEFAULT 0,
    translation_stale_bg INTEGER NOT NULL DEFAULT 0,
    translation_stale_en INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Managed product taxonomy (dynamic-categories). Three independent facets:
-- product type (candles/boxes), category/tier (small/medium/premium), and
-- multi-select labels (winter/gift/floral/...). Slugs are immutable keys;
-- name_en/name_bg are display data. is_active hides a term from new-assignment
-- controls and public filters without deleting referencing products.
CREATE TABLE IF NOT EXISTS product_types (
    slug        TEXT PRIMARY KEY,
    name_en     TEXT NOT NULL,
    name_bg     TEXT,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS product_categories (
    slug        TEXT PRIMARY KEY,
    name_en     TEXT NOT NULL,
    name_bg     TEXT,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS product_labels (
    slug        TEXT PRIMARY KEY,
    name_en     TEXT NOT NULL,
    name_bg     TEXT,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS product_label_assignments (
    product_id  TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    label_slug  TEXT NOT NULL REFERENCES product_labels(slug) ON DELETE RESTRICT,
    PRIMARY KEY (product_id, label_slug)
);

CREATE INDEX IF NOT EXISTS idx_label_assignments_label
    ON product_label_assignments(label_slug);
CREATE INDEX IF NOT EXISTS idx_products_type_slug ON products(product_type_slug);
CREATE INDEX IF NOT EXISTS idx_products_category_slug ON products(category_slug);

-- Lightweight migration marker table (dynamic-categories). A row per applied
-- one-shot data migration makes marker-guarded backfills idempotent.
CREATE TABLE IF NOT EXISTS schema_migrations (
    name        TEXT PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Records how each distinct legacy products.category value maps to a label slug,
-- so the exact original-value-to-label assignment is auditable and repeatable.
CREATE TABLE IF NOT EXISTS taxonomy_category_migration (
    original_value TEXT PRIMARY KEY,
    label_slug     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS product_images (
    id            TEXT PRIMARY KEY,
    product_id    TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    image_url     TEXT NOT NULL,
    thumbnail_url TEXT NOT NULL,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    is_primary    INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_product_images_product
    ON product_images(product_id, sort_order);
CREATE UNIQUE INDEX IF NOT EXISTS idx_product_images_one_primary
    ON product_images(product_id) WHERE is_primary = 1;

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
    -- NOTE: quantity capped at 10 to match cart_max_quantity_per_item in config.
    -- Existing DBs created before this change keep the older CHECK (up to 99) since
    -- the schema uses IF NOT EXISTS and no migration runs. Fresh DBs enforce 10.
    quantity    INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 1 AND quantity <= 10),
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
    delivery_method TEXT CHECK (delivery_method IN ('office', 'door')),
    delivery_courier TEXT CHECK (delivery_courier IN ('speedy', 'econt')),
    delivery_details TEXT,  -- JSON blob (DeliveryOffice or DeliveryDoor)
    -- Shipment tracking (populated on the 'shipped' transition; NULL otherwise).
    tracking_number  TEXT,
    tracking_carrier TEXT,
    tracking_url     TEXT,
    -- Customer locale snapshotted at checkout (email language is a fact of the
    -- order, not a session lookup — see email-notifications design Decision 8).
    locale      TEXT NOT NULL DEFAULT 'en',
    notes       TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_orders_session_id ON orders(session_id);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

-- Transactional email outbox + audit trail (email-notifications Decisions 11, 25).
-- A 'queued' row is written in the same transaction as the order state change
-- (durable intent); the sweeper drives it to a terminal state.
CREATE TABLE IF NOT EXISTS order_emails (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        TEXT NOT NULL REFERENCES orders(id),
    event           TEXT NOT NULL,  -- placed | shipped | delivered | cancelled | admin_new_order
    recipient       TEXT NOT NULL,
    -- queued | sent | failed | failed_permanent
    --   | skipped_duplicate | skipped_in_flight | skipped_suppressed
    status          TEXT NOT NULL,
    reason          TEXT,           -- provider error (failed) or skip detail
    attempts        INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TEXT,           -- backoff gate; NULL = eligible immediately
    sent_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_order_emails_order_id ON order_emails(order_id);
-- DB-level idempotency arbiter: at most one successful send per (order_id, event).
CREATE UNIQUE INDEX IF NOT EXISTS idx_order_emails_sent_unique
    ON order_emails(order_id, event) WHERE status = 'sent';

-- One active sender per (order_id, event): the claim the 2 prod workers' sweepers
-- race on. SQLite's single-writer property makes acquisition atomic for free.
CREATE TABLE IF NOT EXISTS order_email_send_claims (
    order_id         TEXT NOT NULL REFERENCES orders(id),
    event            TEXT NOT NULL,
    status           TEXT NOT NULL,  -- in_flight | sent | failed
    lease_expires_at TEXT,
    updated_at       TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (order_id, event)
);

-- Suppressed recipients: hard bounces / complaints (email-deliverability Decision 15).
CREATE TABLE IF NOT EXISTS suppressed_emails (
    email        TEXT PRIMARY KEY,
    reason       TEXT NOT NULL,  -- hard_bounce | soft_bounce | fbl_complaint
    suppressed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Contact form messages: persisted inquiry + durable owner-notification state.
CREATE TABLE IF NOT EXISTS contact_messages (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    name                  TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 100),
    email                 TEXT NOT NULL CHECK (length(email) BETWEEN 3 AND 254),
    message               TEXT NOT NULL CHECK (length(message) BETWEEN 1 AND 2000),
    locale                TEXT NOT NULL DEFAULT 'en' CHECK (locale IN ('en', 'bg')),
    ip_address            TEXT,
    email_status          TEXT NOT NULL DEFAULT 'queued'
                          CHECK (email_status IN (
                              'queued', 'in_flight', 'sent', 'failed',
                              'failed_permanent', 'skipped_suppressed'
                          )),
    email_attempts        INTEGER NOT NULL DEFAULT 0 CHECK (email_attempts >= 0),
    email_next_attempt_at TEXT,
    email_claimed_until   TEXT,
    email_sent_at         TEXT,
    email_error           TEXT,
    created_at            TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_contact_messages_created_at
    ON contact_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_contact_messages_email_status
    ON contact_messages(email_status, email_next_attempt_at);
CREATE INDEX IF NOT EXISTS idx_contact_messages_ip_created
    ON contact_messages(ip_address, created_at);

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
    product_type_slug TEXT NOT NULL DEFAULT 'candles',
    category_slug     TEXT,
    stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    is_active   INTEGER NOT NULL DEFAULT 1,
    is_featured INTEGER NOT NULL DEFAULT 0,
    translation_stale_bg INTEGER NOT NULL DEFAULT 0,
    translation_stale_en INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

_PRODUCT_IMAGES_TABLE_SQL = """\
CREATE TABLE IF NOT EXISTS product_images (
    id            TEXT PRIMARY KEY,
    product_id    TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    image_url     TEXT NOT NULL,
    thumbnail_url TEXT NOT NULL,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    is_primary    INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_product_images_product
    ON product_images(product_id, sort_order);
CREATE UNIQUE INDEX IF NOT EXISTS idx_product_images_one_primary
    ON product_images(product_id) WHERE is_primary = 1;
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
    "product_type_slug",
    "category_slug",
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
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _migrate_existing_schema(conn)
        conn.executescript(_SCHEMA_SQL)
        _migrate_taxonomy(conn)
        _migrate_product_label_assignments_table(conn)
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


def _legacy_product_image_id(product_id: str) -> str:
    """Return a stable UUID hex for a migrated legacy product image."""
    return uuid.uuid5(uuid.NAMESPACE_URL, f"atelier-marie/product-image/{product_id}").hex


def _legacy_thumbnail_url(image_url: str) -> str:
    """Derive the old thumbnail URL convention from a legacy image URL."""
    path = Path(image_url)
    if path.suffix:
        return str(path.with_name(f"{path.stem}_thumb{path.suffix}"))
    return f"{image_url.rstrip('/')}_thumb.webp"


def _legacy_product_images_from_products(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """Read legacy products.image_url values before the products table is rebuilt."""
    product_columns = _table_columns(conn, "products")
    if "image_url" not in product_columns:
        return []

    rows = conn.execute(
        """
        SELECT id, image_url
        FROM products
        WHERE image_url IS NOT NULL AND TRIM(image_url) != ''
        """
    ).fetchall()
    return [(row["id"], row["image_url"]) for row in rows]


def _seed_product_images_from_legacy_rows(
    conn: sqlite3.Connection,
    legacy_images: list[tuple[str, str]],
) -> None:
    """Insert legacy image URLs into product_images exactly once."""
    for product_id, image_url in legacy_images:
        image_id = _legacy_product_image_id(product_id)
        conn.execute(
            """
            INSERT OR IGNORE INTO product_images (
                id, product_id, image_url, thumbnail_url, sort_order, is_primary, created_at
            ) VALUES (?, ?, ?, ?, 0, 1, datetime('now'))
            """,
            (image_id, product_id, image_url, _legacy_thumbnail_url(image_url)),
        )


def _migrate_existing_schema(conn: sqlite3.Connection) -> None:
    """Bring pre-bilingual SQLite files up to the current schema."""
    conn.executescript(_PRODUCT_FTS_RESET_SQL)

    if _table_exists(conn, "products"):
        legacy_images = _legacy_product_images_from_products(conn)
        _migrate_products_table(conn)
        conn.executescript(_PRODUCT_IMAGES_TABLE_SQL)
        _seed_product_images_from_legacy_rows(conn, legacy_images)

    if _table_exists(conn, "sessions"):
        session_columns = _table_columns(conn, "sessions")
        _add_column_if_missing(
            conn,
            "sessions",
            session_columns,
            "preferred_locale",
            "preferred_locale TEXT NOT NULL DEFAULT 'en'",
        )

    if _table_exists(conn, "orders"):
        order_columns = _table_columns(conn, "orders")
        # Structured delivery columns (added by shipping-courier-integration).
        # CHECK constraints omitted here because SQLite ALTER TABLE ADD COLUMN
        # doesn't support them; validation happens at the Pydantic layer.
        _add_column_if_missing(
            conn, "orders", order_columns, "delivery_method", "delivery_method TEXT"
        )
        _add_column_if_missing(
            conn, "orders", order_columns, "delivery_courier", "delivery_courier TEXT"
        )
        _add_column_if_missing(
            conn, "orders", order_columns, "delivery_details", "delivery_details TEXT"
        )
        # Shipment tracking + locale snapshot (email-notifications).
        _add_column_if_missing(
            conn, "orders", order_columns, "tracking_number", "tracking_number TEXT"
        )
        _add_column_if_missing(
            conn, "orders", order_columns, "tracking_carrier", "tracking_carrier TEXT"
        )
        _add_column_if_missing(conn, "orders", order_columns, "tracking_url", "tracking_url TEXT")
        _add_column_if_missing(
            conn, "orders", order_columns, "locale", "locale TEXT NOT NULL DEFAULT 'en'"
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
        _column_expr(columns, "product_type_slug", "'candles'"),
        _column_expr(columns, "category_slug"),
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


def _migrate_product_label_assignments_table(conn: sqlite3.Connection) -> None:
    """Add the product_labels FK to existing label assignment tables.

    SQLite cannot add foreign keys with ALTER TABLE. Older dynamic-categories DBs
    created product_label_assignments without a label_slug FK, so rebuild the
    table once and copy only assignments that still reference real products and
    labels.
    """
    if not _table_exists(conn, "product_label_assignments"):
        return

    fks = conn.execute("PRAGMA foreign_key_list(product_label_assignments)").fetchall()
    has_label_fk = any(row[2] == "product_labels" and row[3] == "label_slug" for row in fks)
    if has_label_fk:
        return

    conn.execute("DROP TABLE IF EXISTS product_label_assignments_new")
    conn.execute(
        """
        CREATE TABLE product_label_assignments_new (
            product_id  TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            label_slug  TEXT NOT NULL REFERENCES product_labels(slug) ON DELETE RESTRICT,
            PRIMARY KEY (product_id, label_slug)
        )
        """
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO product_label_assignments_new (product_id, label_slug)
        SELECT pla.product_id, pla.label_slug
        FROM product_label_assignments pla
        JOIN products p ON p.id = pla.product_id
        JOIN product_labels pl ON pl.slug = pla.label_slug
        """
    )
    conn.execute("DROP TABLE product_label_assignments")
    conn.execute("ALTER TABLE product_label_assignments_new RENAME TO product_label_assignments")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_label_assignments_label "
        "ON product_label_assignments(label_slug)"
    )


def _rebuild_product_fts(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "products"):
        return
    conn.execute("INSERT INTO products_fts_en(products_fts_en) VALUES ('rebuild')")
    conn.execute("INSERT INTO products_fts_bg(products_fts_bg) VALUES ('rebuild')")


# ---------------------------------------------------------------------------
# Managed product taxonomy migration (dynamic-categories)
# ---------------------------------------------------------------------------

# Starter taxonomy so a fresh shop is usable. These are startup seed data only —
# they do NOT replace admin management and must not be duplicated as frontend
# constants. Each entry: (slug, name_en, name_bg, sort_order).
_SEED_PRODUCT_TYPES = [
    ("candles", "Candles", "Свещи", 0),
    ("boxes", "Boxes", "Кутии", 1),
]
_SEED_CATEGORIES = [
    ("small", "Small", "Малка", 0),
    ("medium", "Medium", "Средна", 1),
    ("premium", "Premium", "Премиум", 2),
]
_SEED_LABELS = [
    ("floral", "Floral", "Флорални", 0),
    ("woody", "Woody", "Дървесни", 1),
    ("fresh", "Fresh", "Свежи", 2),
    ("gourmand", "Gourmand", "Гурме", 3),
    ("spicy", "Spicy", "Пикантни", 4),
    ("citrus", "Citrus", "Цитрусови", 5),
    ("winter", "Winter", "Зима", 6),
    ("gift", "Gift", "Подарък", 7),
    ("christmas", "Christmas", "Коледа", 8),
]

_TAXONOMY_MIGRATION_MARKER = "product_taxonomy_v1"


def _seed_taxonomy_table(
    conn: sqlite3.Connection,
    table: str,
    rows: list[tuple[str, str, str | None, int]],
) -> None:
    """Insert seed terms if absent. Idempotent (INSERT OR IGNORE by slug)."""
    conn.executemany(
        f"INSERT OR IGNORE INTO {table} "  # noqa: S608 — table is a module constant
        "(slug, name_en, name_bg, sort_order) VALUES (?, ?, ?, ?)",
        rows,
    )


def _migration_applied(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute("SELECT 1 FROM schema_migrations WHERE name = ?", (name,)).fetchone()
    return row is not None


def _backfill_legacy_categories(conn: sqlite3.Connection) -> None:
    """Convert distinct legacy products.category values into managed labels.

    Reads each distinct non-null value BEFORE any rewrite, creates or reuses a
    label slug, records the exact original-value-to-slug mapping, and assigns
    the label to products holding that exact original value. Distinct values
    that slugify to the same base get deterministic suffixes.
    """
    rows = conn.execute(
        "SELECT DISTINCT category FROM products "
        "WHERE category IS NOT NULL AND TRIM(category) != '' "
        "ORDER BY category"
    ).fetchall()
    if not rows:
        return

    # Existing label slugs — includes seeds inserted earlier this run.
    existing = {r["slug"] for r in conn.execute("SELECT slug FROM product_labels")}
    # Slugs claimed by a distinct original value during this backfill; used to
    # force suffixing when two distinct originals collide on the same base.
    claimed: set[str] = set()
    next_sort = 100  # place migrated labels after seed labels

    for row in rows:
        original = row["category"]
        base = slugify(original)

        if base in existing and base not in claimed:
            # Reuse an existing label (seed or prior) for this base.
            slug = base
        else:
            slug = unique_slug(base, existing | claimed)
            conn.execute(
                "INSERT INTO product_labels (slug, name_en, name_bg, sort_order) "
                "VALUES (?, ?, ?, ?)",
                (slug, original.strip(), None, next_sort),
            )
            existing.add(slug)
            next_sort += 1

        claimed.add(slug)
        conn.execute(
            "INSERT OR IGNORE INTO taxonomy_category_migration "
            "(original_value, label_slug) VALUES (?, ?)",
            (original, slug),
        )
        conn.execute(
            "INSERT OR IGNORE INTO product_label_assignments (product_id, label_slug) "
            "SELECT id, ? FROM products WHERE category = ?",
            (slug, original),
        )


def _migrate_taxonomy(conn: sqlite3.Connection) -> None:
    """Seed starter taxonomy and (once) backfill labels from legacy categories."""
    # Marker guards the one-shot backfill so re-runs are a no-op even when seed
    # taxonomy already exists (the marker, not "seeds present", is the gate).
    if _migration_applied(conn, _TAXONOMY_MIGRATION_MARKER):
        return

    _seed_taxonomy_table(conn, "product_types", _SEED_PRODUCT_TYPES)
    _seed_taxonomy_table(conn, "product_categories", _SEED_CATEGORIES)
    _seed_taxonomy_table(conn, "product_labels", _SEED_LABELS)

    _backfill_legacy_categories(conn)
    # Default any product missing a product type to candles; leave category NULL.
    conn.execute(
        "UPDATE products SET product_type_slug = 'candles' "
        "WHERE product_type_slug IS NULL OR product_type_slug = ''"
    )
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations (name) VALUES (?)",
        (_TAXONOMY_MIGRATION_MARKER,),
    )


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
