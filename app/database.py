"""SQLite database connection and schema management."""

# ruff: noqa: E501

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
    safety_warnings_en TEXT,
    safety_warnings_bg TEXT,
    care_instructions_en TEXT,
    care_instructions_bg TEXT,
    materials   TEXT,
    days_to_craft INTEGER,
    price_cents INTEGER NOT NULL CHECK (price_cents > 0),
    -- Legacy free-text category. Superseded by managed taxonomy (product_type_slug,
    -- category_slug, product_label_assignments). Kept for migration compatibility.
    category    TEXT,
    -- Managed taxonomy references (dynamic-categories). Slugs, not display names.
    product_type_slug TEXT NOT NULL DEFAULT 'candles',
    category_slug     TEXT,
    discount_percent INTEGER CHECK (discount_percent IS NULL OR discount_percent BETWEEN 1 AND 99),
    discount_starts_at TEXT,
    discount_ends_at TEXT,
    stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    weight_grams INTEGER NOT NULL DEFAULT 300 CHECK (weight_grams > 0),
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

-- Admin-managed FAQ (admin-managed-faq). Two tables mirror the dynamic-categories
-- bilingual pattern: `_en` required, `_bg` nullable resolved with COALESCE.
-- Sections carry stable anchor slugs (candles/care/custom/shipping) that product
-- pages deep-link to, so slugs are immutable; only titles/icon/order are editable.
CREATE TABLE IF NOT EXISTS faq_sections (
    slug        TEXT PRIMARY KEY,
    title_en    TEXT NOT NULL,
    title_bg    TEXT,
    icon        TEXT,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS faq_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    section      TEXT NOT NULL REFERENCES faq_sections(slug),
    question_en  TEXT NOT NULL,
    question_bg  TEXT,
    answer_en    TEXT NOT NULL,
    answer_bg    TEXT,
    sort_order   INTEGER NOT NULL DEFAULT 0,
    is_published INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_faq_items_section_order ON faq_items(section, sort_order);

CREATE TABLE IF NOT EXISTS product_images (
    id            TEXT PRIMARY KEY,
    product_id    TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    image_url     TEXT NOT NULL,
    thumbnail_url TEXT NOT NULL,
    zoom_url      TEXT,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    is_primary    INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_product_images_product
    ON product_images(product_id, sort_order);
CREATE UNIQUE INDEX IF NOT EXISTS idx_product_images_one_primary
    ON product_images(product_id) WHERE is_primary = 1;

CREATE TABLE IF NOT EXISTS product_videos (
    id              TEXT PRIMARY KEY,
    product_id      TEXT NOT NULL UNIQUE REFERENCES products(id) ON DELETE CASCADE,
    status          TEXT NOT NULL CHECK (status IN ('queued', 'transcoding', 'ready', 'failed')),
    source_path     TEXT,
    video_url       TEXT,
    poster_url      TEXT,
    duration_secs   REAL,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    failure_reason  TEXT,
    lease_expires_at TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_product_videos_status
    ON product_videos(status);

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

CREATE TABLE IF NOT EXISTS analytics_consents (
    session_id      TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
    analytics       INTEGER NOT NULL CHECK (analytics IN (0, 1)),
    consent_version TEXT NOT NULL,
    locale          TEXT NOT NULL DEFAULT 'en' CHECK (locale IN ('en', 'bg')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_analytics_consents_current
    ON analytics_consents(session_id, consent_version, analytics);

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
    internal_sequence INTEGER UNIQUE,
    order_number TEXT UNIQUE,
    session_id  TEXT NOT NULL,
    user_id     TEXT REFERENCES users(id),
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')),
    total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
    customer_email TEXT NOT NULL,
    customer_name  TEXT,
    -- Shipping price + provenance (shipping-pricing — Phase A). shipping_cents
    -- sums with items subtotal into total_cents. Provenance records how the
    -- price was derived, for later reconciliation.
    shipping_cents INTEGER NOT NULL DEFAULT 0 CHECK (shipping_cents >= 0),
    shipping_price_source TEXT NOT NULL DEFAULT 'live',
    shipping_is_fallback INTEGER NOT NULL DEFAULT 0,
    shipping_quoted_at TEXT,
    delivery_method TEXT CHECK (delivery_method IN ('office', 'door')),
    delivery_courier TEXT CHECK (delivery_courier IN ('speedy', 'econt')),
    delivery_details TEXT,  -- JSON blob (DeliveryOffice or DeliveryDoor)
    -- Shipment tracking (populated on the 'shipped' transition; NULL otherwise).
    tracking_number  TEXT,
    tracking_carrier TEXT,
    tracking_url     TEXT,
    -- Courier transit status (Speedy /track normalized; display-only, does NOT
    -- drive the order state machine — speedy-integration Decision 4). NULL until
    -- a track poll runs.
    courier_status   TEXT,
    -- Printable-label URL/id when a waybill was created via the courier API.
    label_url        TEXT,
    -- Customer locale snapshotted at checkout (email language is a fact of the
    -- order, not a session lookup — see email-notifications design Decision 8).
    locale      TEXT NOT NULL DEFAULT 'en',
    notes       TEXT,
    -- Payment axis (orthogonal to order status — payment-integration design).
    payment_method  TEXT NOT NULL DEFAULT 'cod'
                    CHECK (payment_method IN ('cod', 'card', 'bank_transfer')),
    payment_status  TEXT NOT NULL DEFAULT 'cod_pending'
                    CHECK (payment_status IN (
                        'pending', 'paid', 'cod_pending', 'failed', 'refunded'
                    )),
    reserved_until TEXT,
    paid_at TEXT,
    collected_at TEXT,
    payment_return_token TEXT UNIQUE,
    stripe_checkout_session_id TEXT,
    stripe_payment_intent_id   TEXT,
    analytics_consent INTEGER NOT NULL DEFAULT 0 CHECK (analytics_consent IN (0, 1)),
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS payments (
    id          TEXT PRIMARY KEY,
    order_id    TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    provider    TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
    currency    TEXT NOT NULL DEFAULT 'EUR',
    stripe_checkout_session_id TEXT UNIQUE,
    stripe_payment_intent_id   TEXT,
    provider_status TEXT,
    provider_details TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS payment_events (
    id          TEXT PRIMARY KEY,
    order_id    TEXT REFERENCES orders(id) ON DELETE CASCADE,
    payment_id  TEXT REFERENCES payments(id) ON DELETE SET NULL,
    event_type  TEXT NOT NULL,
    source      TEXT NOT NULL DEFAULT 'system',
    stripe_event_id TEXT UNIQUE,
    stripe_event_type TEXT,
    provider    TEXT,
    provider_status TEXT,
    processing_status TEXT NOT NULL DEFAULT 'processed',
    details     TEXT,
    admin_user_id TEXT,
    admin_email TEXT,
    admin_note  TEXT,
    request_id  TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS site_settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    value_type  TEXT NOT NULL DEFAULT 'json',
    is_public   INTEGER NOT NULL DEFAULT 0 CHECK (is_public IN (0, 1)),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS site_setting_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT NOT NULL,
    old_value   TEXT,
    new_value   TEXT NOT NULL,
    admin_id    TEXT,
    admin_email TEXT,
    request_id  TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Stripe webhook dedup table — mirrors order_emails pattern (payment-integration Decision 7).
CREATE TABLE IF NOT EXISTS stripe_events (
    event_id    TEXT PRIMARY KEY,   -- Stripe's evt_xxx — dedup key
    order_id    TEXT,               -- nullable: some events may not map to an order
    event_type  TEXT NOT NULL,      -- e.g. 'checkout.session.completed'
    received_at TEXT NOT NULL       -- YYYY-MM-DD HH:MM:SS UTC
);

CREATE TABLE IF NOT EXISTS payment_rate_limit_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    action     TEXT NOT NULL,
    scope      TEXT NOT NULL,
    key        TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS admin_alerts (
    id          TEXT PRIMARY KEY,
    alert_type  TEXT NOT NULL,
    order_id    TEXT REFERENCES orders(id) ON DELETE CASCADE,
    source      TEXT NOT NULL DEFAULT 'system',
    severity    TEXT NOT NULL DEFAULT 'warning',
    title       TEXT NOT NULL,
    message     TEXT NOT NULL,
    details     TEXT,
    is_read     INTEGER NOT NULL DEFAULT 0 CHECK (is_read IN (0, 1)),
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_orders_session_id ON orders(session_id);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_internal_sequence ON orders(internal_sequence);
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_order_number ON orders(order_number);
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_payment_return_token
    ON orders(payment_return_token);
CREATE INDEX IF NOT EXISTS idx_orders_payment_status ON orders(payment_status);
CREATE INDEX IF NOT EXISTS idx_orders_payment_method ON orders(payment_method);
CREATE INDEX IF NOT EXISTS idx_orders_reserved_until ON orders(reserved_until);
CREATE INDEX IF NOT EXISTS idx_orders_stripe_checkout_session_id
    ON orders(stripe_checkout_session_id);
CREATE INDEX IF NOT EXISTS idx_orders_stripe_payment_intent_id
    ON orders(stripe_payment_intent_id);
CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_provider ON payments(provider);
CREATE INDEX IF NOT EXISTS idx_payments_stripe_checkout_session_id
    ON payments(stripe_checkout_session_id);
CREATE INDEX IF NOT EXISTS idx_payments_stripe_payment_intent_id
    ON payments(stripe_payment_intent_id);
CREATE INDEX IF NOT EXISTS idx_payment_events_order_id ON payment_events(order_id, created_at);
CREATE INDEX IF NOT EXISTS idx_payment_events_stripe_event_id
    ON payment_events(stripe_event_id);
CREATE INDEX IF NOT EXISTS idx_payment_rate_limit_lookup
    ON payment_rate_limit_events(action, scope, key, created_at);
CREATE INDEX IF NOT EXISTS idx_admin_alerts_unread_created
    ON admin_alerts(is_read, created_at);
CREATE INDEX IF NOT EXISTS idx_admin_alerts_order_id
    ON admin_alerts(order_id, created_at);
CREATE INDEX IF NOT EXISTS idx_site_setting_events_key_created
    ON site_setting_events(setting_key, created_at);

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

-- Promotion campaigns: admin management records over the per-product discount
-- fields. Cart/checkout/public pricing NEVER read these rows — runtime pricing
-- stays on products (see promotion-campaign-management design Decision 1).
CREATE TABLE IF NOT EXISTS promotion_campaigns (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    note          TEXT,
    discount_percent INTEGER NOT NULL
                  CHECK (discount_percent BETWEEN 1 AND 99),
    discount_starts_at TEXT,
    discount_ends_at   TEXT,
    target_type   TEXT NOT NULL CHECK (target_type IN ('ids', 'filter')),
    target_ids    TEXT,   -- JSON array of product IDs when target_type = 'ids'
    target_filter TEXT,   -- JSON filter descriptor when target_type = 'filter'
    applied_at    TEXT,   -- NULL until first applied
    removed_at    TEXT,   -- NULL unless discount has been removed
    last_result   TEXT,   -- JSON summary of the most recent apply/remove result
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_promotion_campaigns_created
    ON promotion_campaigns(created_at);

-- Per-product apply record: the resolved targets and the exact discount values
-- written, so conservative removal can compare current fields to last-applied.
CREATE TABLE IF NOT EXISTS promotion_campaign_products (
    campaign_id       TEXT NOT NULL
                      REFERENCES promotion_campaigns(id) ON DELETE CASCADE,
    product_id        TEXT NOT NULL,
    applied_percent   INTEGER,
    applied_starts_at TEXT,
    applied_ends_at   TEXT,
    PRIMARY KEY (campaign_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_promotion_campaign_products_product
    ON promotion_campaign_products(product_id);

-- Managed top-of-site announcement banner. Singleton row (id = 'default').
-- `version` bumps whenever visible content or schedule changes so the public
-- dismiss key changes and previously-dismissed old copy no longer suppresses it.
CREATE TABLE IF NOT EXISTS site_banners (
    id            TEXT PRIMARY KEY DEFAULT 'default',
    message_en    TEXT,
    message_bg    TEXT,
    link_label_en TEXT,
    link_label_bg TEXT,
    link_url      TEXT,
    is_enabled    INTEGER NOT NULL DEFAULT 0 CHECK (is_enabled IN (0, 1)),
    starts_at     TEXT,
    ends_at       TEXT,
    version       INTEGER NOT NULL DEFAULT 1,
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Admin-managed delivery availability switches. Singleton row (id = 'default').
-- All methods default to enabled to preserve existing checkout behavior until an
-- admin explicitly pauses a courier/method pair.
CREATE TABLE IF NOT EXISTS delivery_settings (
    id                    TEXT PRIMARY KEY DEFAULT 'default',
    speedy_office_enabled INTEGER NOT NULL DEFAULT 1 CHECK (speedy_office_enabled IN (0, 1)),
    speedy_door_enabled   INTEGER NOT NULL DEFAULT 1 CHECK (speedy_door_enabled IN (0, 1)),
    econt_office_enabled  INTEGER NOT NULL DEFAULT 1 CHECK (econt_office_enabled IN (0, 1)),
    econt_door_enabled    INTEGER NOT NULL DEFAULT 1 CHECK (econt_door_enabled IN (0, 1)),
    cod_enabled           INTEGER NOT NULL DEFAULT 1 CHECK (cod_enabled IN (0, 1)),
    card_enabled          INTEGER NOT NULL DEFAULT 1 CHECK (card_enabled IN (0, 1)),
    bank_transfer_enabled INTEGER NOT NULL DEFAULT 1 CHECK (bank_transfer_enabled IN (0, 1)),
    updated_at            TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Atelier story page content (about-management). Slugs and types are fixed
-- server vocabulary; admin can edit text/images, publish state, and order.
CREATE TABLE IF NOT EXISTS about_sections (
    slug          TEXT PRIMARY KEY,
    type          TEXT NOT NULL,
    heading_en    TEXT NOT NULL,
    heading_bg    TEXT,
    subheading_en TEXT,
    subheading_bg TEXT,
    body_en       TEXT,
    body_bg       TEXT,
    cta_label_en  TEXT,
    cta_label_bg  TEXT,
    cta_href      TEXT,
    image_id      TEXT,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    is_published  INTEGER NOT NULL DEFAULT 1 CHECK (is_published IN (0, 1)),
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS about_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    section      TEXT NOT NULL REFERENCES about_sections(slug) ON DELETE CASCADE,
    title_en     TEXT NOT NULL,
    title_bg     TEXT,
    text_en      TEXT,
    text_bg      TEXT,
    image_id     TEXT,
    link_href    TEXT,
    sort_order   INTEGER NOT NULL DEFAULT 0,
    is_published INTEGER NOT NULL DEFAULT 1 CHECK (is_published IN (0, 1)),
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_about_items_section_order
    ON about_items(section, sort_order);

-- Auto-update updated_at on row modification
CREATE TRIGGER IF NOT EXISTS products_updated_at AFTER UPDATE ON products
BEGIN
    UPDATE products SET updated_at = datetime('now') WHERE rowid = NEW.rowid;
END;

CREATE TRIGGER IF NOT EXISTS product_videos_updated_at AFTER UPDATE ON product_videos
BEGIN
    UPDATE product_videos SET updated_at = datetime('now') WHERE rowid = NEW.rowid;
END;

CREATE TRIGGER IF NOT EXISTS orders_updated_at AFTER UPDATE ON orders
BEGIN
    UPDATE orders SET updated_at = datetime('now') WHERE rowid = NEW.rowid;
END;

CREATE TRIGGER IF NOT EXISTS payments_updated_at AFTER UPDATE ON payments
BEGIN
    UPDATE payments SET updated_at = datetime('now') WHERE rowid = NEW.rowid;
END;

CREATE TRIGGER IF NOT EXISTS site_settings_updated_at AFTER UPDATE ON site_settings
BEGIN
    UPDATE site_settings SET updated_at = datetime('now') WHERE rowid = NEW.rowid;
END;

CREATE TRIGGER IF NOT EXISTS delivery_settings_updated_at AFTER UPDATE ON delivery_settings
BEGIN
    UPDATE delivery_settings SET updated_at = datetime('now') WHERE rowid = NEW.rowid;
END;

CREATE TRIGGER IF NOT EXISTS faq_sections_updated_at AFTER UPDATE ON faq_sections
BEGIN
    UPDATE faq_sections SET updated_at = datetime('now') WHERE rowid = NEW.rowid;
END;

CREATE TRIGGER IF NOT EXISTS faq_items_updated_at AFTER UPDATE ON faq_items
BEGIN
    UPDATE faq_items SET updated_at = datetime('now') WHERE rowid = NEW.rowid;
END;

-- Full-text search for products — English index (content-backed via triggers).
-- Indexes name + description only; the legacy `category` column is no longer
-- written (taxonomy moved to product_type_slug/category_slug/labels), so it was
-- dropped from the index to keep search coverage consistent across all products.
CREATE VIRTUAL TABLE IF NOT EXISTS products_fts_en USING fts5(
    name_en,
    description_en,
    content='products',
    content_rowid='rowid'
);

-- Full-text search for products — Bulgarian index (content-backed via triggers)
CREATE VIRTUAL TABLE IF NOT EXISTS products_fts_bg USING fts5(
    name_bg,
    description_bg,
    content='products',
    content_rowid='rowid'
);

-- Sync triggers: keep English FTS index in sync with products table
CREATE TRIGGER IF NOT EXISTS products_fts_en_insert AFTER INSERT ON products
BEGIN
    INSERT INTO products_fts_en(rowid, name_en, description_en)
    VALUES (NEW.rowid, NEW.name_en, COALESCE(NEW.description_en, ''));
END;

CREATE TRIGGER IF NOT EXISTS products_fts_en_delete BEFORE DELETE ON products
BEGIN
    INSERT INTO products_fts_en(products_fts_en, rowid, name_en, description_en)
    VALUES ('delete', OLD.rowid, OLD.name_en, COALESCE(OLD.description_en, ''));
END;

CREATE TRIGGER IF NOT EXISTS products_fts_en_update AFTER UPDATE ON products
BEGIN
    INSERT INTO products_fts_en(products_fts_en, rowid, name_en, description_en)
    VALUES ('delete', OLD.rowid, OLD.name_en, COALESCE(OLD.description_en, ''));
    INSERT INTO products_fts_en(rowid, name_en, description_en)
    VALUES (NEW.rowid, NEW.name_en, COALESCE(NEW.description_en, ''));
END;

-- Sync triggers: keep Bulgarian FTS index in sync with products table
CREATE TRIGGER IF NOT EXISTS products_fts_bg_insert AFTER INSERT ON products
BEGIN
    INSERT INTO products_fts_bg(rowid, name_bg, description_bg)
    VALUES (NEW.rowid, COALESCE(NEW.name_bg, ''), COALESCE(NEW.description_bg, ''));
END;

CREATE TRIGGER IF NOT EXISTS products_fts_bg_delete BEFORE DELETE ON products
BEGIN
    INSERT INTO products_fts_bg(products_fts_bg, rowid, name_bg, description_bg)
    VALUES ('delete', OLD.rowid, COALESCE(OLD.name_bg, ''), COALESCE(OLD.description_bg, ''));
END;

CREATE TRIGGER IF NOT EXISTS products_fts_bg_update AFTER UPDATE ON products
BEGIN
    INSERT INTO products_fts_bg(products_fts_bg, rowid, name_bg, description_bg)
    VALUES ('delete', OLD.rowid, COALESCE(OLD.name_bg, ''), COALESCE(OLD.description_bg, ''));
    INSERT INTO products_fts_bg(rowid, name_bg, description_bg)
    VALUES (NEW.rowid, COALESCE(NEW.name_bg, ''), COALESCE(NEW.description_bg, ''));
END;
"""

_PRODUCTS_TABLE_SQL = """\
CREATE TABLE products_new (
    id          TEXT PRIMARY KEY,
    name_en     TEXT NOT NULL,
    name_bg     TEXT,
    description_en TEXT,
    description_bg TEXT,
    safety_warnings_en TEXT,
    safety_warnings_bg TEXT,
    care_instructions_en TEXT,
    care_instructions_bg TEXT,
    materials   TEXT,
    days_to_craft INTEGER,
    price_cents INTEGER NOT NULL CHECK (price_cents > 0),
    category    TEXT,
    product_type_slug TEXT NOT NULL DEFAULT 'candles',
    category_slug     TEXT,
    discount_percent INTEGER CHECK (discount_percent IS NULL OR discount_percent BETWEEN 1 AND 99),
    discount_starts_at TEXT,
    discount_ends_at TEXT,
    stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    weight_grams INTEGER NOT NULL DEFAULT 300 CHECK (weight_grams > 0),
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
    zoom_url      TEXT,
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
    "safety_warnings_en",
    "safety_warnings_bg",
    "care_instructions_en",
    "care_instructions_bg",
    "materials",
    "days_to_craft",
    "price_cents",
    "category",
    "product_type_slug",
    "category_slug",
    "discount_percent",
    "discount_starts_at",
    "discount_ends_at",
    "stock",
    "weight_grams",
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
        _migrate_delivery_settings(conn)
        _backfill_order_payment_summary(conn)
        _migrate_taxonomy(conn)
        _migrate_product_label_assignments_table(conn)
        _seed_site_banner(conn)
        _seed_delivery_settings(conn)
        _seed_about_content(conn)
        _migrate_faq(conn)
        _migrate_faq_returns_policy_reference(conn)
        _rebuild_product_fts(conn)
        conn.commit()
    finally:
        conn.close()

    # Restrict DB file permissions (owner read/write only)
    os.chmod(path, 0o600)


def _seed_site_banner(conn: sqlite3.Connection) -> None:
    """Seed the singleton managed banner from the former static announcement copy.

    Uses INSERT OR IGNORE so a fresh DB gets the previous "free shipping" banner
    (enabled, no window) — preserving current storefront behavior — while any
    later admin edit or disable is never overwritten on subsequent startups.
    """
    conn.execute(
        """
        INSERT OR IGNORE INTO site_banners (
            id, message_en, message_bg, is_enabled, version, updated_at
        ) VALUES (
            'default',
            'Free shipping on orders over €50 ✨',
            'Безплатна доставка за поръчки над 50€ ✨',
            1, 1, datetime('now')
        )
        """
    )


def _migrate_delivery_settings(conn: sqlite3.Connection) -> None:
    """Add newly introduced delivery/payment availability switches."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(delivery_settings)")}
    _add_column_if_missing(
        conn,
        "delivery_settings",
        columns,
        "cod_enabled",
        "cod_enabled INTEGER NOT NULL DEFAULT 1",
    )
    _add_column_if_missing(
        conn,
        "delivery_settings",
        columns,
        "card_enabled",
        "card_enabled INTEGER NOT NULL DEFAULT 1",
    )
    _add_column_if_missing(
        conn,
        "delivery_settings",
        columns,
        "bank_transfer_enabled",
        "bank_transfer_enabled INTEGER NOT NULL DEFAULT 1",
    )


def _seed_delivery_settings(conn: sqlite3.Connection) -> None:
    """Seed the singleton delivery availability row with all methods enabled."""
    conn.execute(
        """
        INSERT OR IGNORE INTO delivery_settings (
            id, speedy_office_enabled, speedy_door_enabled,
            econt_office_enabled, econt_door_enabled,
            cod_enabled, card_enabled, bank_transfer_enabled, updated_at
        ) VALUES ('default', 1, 1, 1, 1, 1, 1, 1, datetime('now'))
        """
    )


_ABOUT_SECTIONS = [
    {
        "slug": "hero",
        "type": "hero",
        "heading_en": "The Atelier Marie",
        "heading_bg": "The Atelier Marie",
        "subheading_en": "Handcrafted Elegance for Beautiful Spaces",
        "subheading_bg": "Ръчно изработена елегантност за красиви пространства",
        "body_en": """At The Atelier Marie, we create handcrafted candles designed to bring beauty, warmth, and a touch of luxury into your home.

Inspired by the elegance of decorative objects, each creation is thoughtfully designed and carefully made in our atelier. From delicate floral arrangements to sculptural designs and personalised pieces, every candle reflects a passion for artistry, detail, and timeless aesthetics.

More than a candle, each creation is a small piece of décor — made to enhance your space, celebrate meaningful moments, and become part of the memories you cherish.""",
        "body_bg": """В The Atelier Marie създаваме ръчно изработени свещи, замислени да внесат красота, топлина и лек досег на лукс във вашия дом.

Вдъхновено от елегантността на декоративните предмети, всяко творение е обмислено с внимание и изработено грижливо в нашето ателие. От нежни флорални аранжировки до скулптурни форми и персонализирани изделия — всяка свещ отразява страст към майсторството, детайла и вечната естетика.

Повече от свещ, всяко творение е малко парче декор — създадено да разкраси вашето пространство, да отбележи значими мигове и да стане част от спомените, които пазите.""",
        "cta_label_en": "Explore our collection",
        "cta_label_bg": "Разгледайте нашата колекция",
        "cta_href": "/products",
        "sort_order": 0,
    },
    {
        "slug": "story",
        "type": "text_image",
        "heading_en": "Our Story",
        "heading_bg": "Нашата история",
        "subheading_en": "From a Creative Idea to a Handmade Atelier",
        "subheading_bg": "От творческа идея до ръчно ателие",
        "body_en": """The Atelier Marie began with a simple thought: *\"I want something this beautiful in my own home.\"*

Inspired by the beauty of decorative candles, the journey started with creating pieces purely out of curiosity and a desire to bring something unique into everyday spaces.

What began as a creative hobby slowly became a passion for designing, experimenting, and creating beautiful objects by hand. Each candle became an opportunity to explore shapes, colours, textures, and fragrances while creating something truly special.

Over time, this passion grew into The Atelier Marie — a place where creativity, craftsmanship, and elegance come together to create candles designed to be enjoyed, admired, and remembered.""",
        "body_bg": """The Atelier Marie започна с една проста мисъл: *„Искам нещо толкова красиво в собствения си дом.“*

Вдъхновено от красотата на декоративните свещи, пътуването започна със създаването на изделия единствено от любопитство и от желание да внесем нещо уникално в ежедневните пространства.

Това, което започна като творческо хоби, постепенно се превърна в страст към проектирането, експериментирането и създаването на красиви предмети на ръка. Всяка свещ се превръщаше във възможност да изследваме форми, цветове, текстури и аромати, докато създаваме нещо наистина специално.

С времето тази страст прерасна в The Atelier Marie — място, където творчеството, майсторството и елегантността се срещат, за да създадат свещи, замислени да бъдат изживени, ценени и помнени.""",
        "cta_label_en": None,
        "cta_label_bg": None,
        "cta_href": None,
        "sort_order": 1,
    },
    {
        "slug": "philosophy",
        "type": "text_band",
        "heading_en": "Our Philosophy",
        "heading_bg": "Нашата философия",
        "subheading_en": "Candles Designed to Be Admired",
        "subheading_bg": "Свещи, създадени, за да им се възхищавате",
        "body_en": """We believe candles can be more than a source of light or fragrance.

They can become decorative pieces that add character, warmth, and beauty to a space. They can transform a room, create an atmosphere, and become part of meaningful moments.

At The Atelier Marie, every creation is designed with the intention of bringing together artistic expression, luxurious fragrance, and thoughtful craftsmanship.

Some pieces are created to be enjoyed through their scent and flame, while others are designed purely as decorative objects to be admired as part of your home.

Every candle is made to bring a little more beauty into everyday life.""",
        "body_bg": """Вярваме, че свещите могат да бъдат повече от източник на светлина или аромат.

Те могат да се превърнат в декоративни предмети, които придават характер, топлина и красота на пространството. Могат да преобразят стаята, да създадат атмосфера и да станат част от значими мигове.

В The Atelier Marie всяко творение е замислено с намерението да обедини артистичен изказ, луксозен аромат и премислено майсторство.

Някои изделия са създадени, за да бъдат изживени чрез своя аромат и пламък, а други са замислени единствено като декоративни предмети, на които да се възхищавате като част от вашия дом.

Всяка свещ е направена, за да внесе малко повече красота в ежедневието.""",
        "cta_label_en": None,
        "cta_label_bg": None,
        "cta_href": None,
        "sort_order": 2,
    },
    {
        "slug": "differentiators",
        "type": "cards",
        "heading_en": "What Makes Our Candles Different",
        "heading_bg": "Какво отличава нашите свещи",
        "subheading_en": "More Than a Candle — A Piece of Art for Your Home",
        "subheading_bg": "Повече от свещ — произведение на изкуството за вашия дом",
        "body_en": None,
        "body_bg": None,
        "cta_label_en": None,
        "cta_label_bg": None,
        "cta_href": None,
        "sort_order": 3,
    },
    {
        "slug": "process",
        "type": "timeline",
        "heading_en": "The Art of Making",
        "heading_bg": "Изкуството на създаването",
        "subheading_en": "Crafted Slowly, Made With Care",
        "subheading_bg": "Изработени бавно, създадени с грижа",
        "body_en": """Every creation begins with an idea.

Before a candle reaches your home, it goes through a careful process of design and craftsmanship. Shapes are considered, moulds are prepared, colours are carefully selected, and every decorative element is thoughtfully arranged.

Each piece is handcrafted through multiple stages, including pouring, shaping, adding details by hand, and allowing the candle time to properly set and develop its final appearance.

Some candles are created in small batches, while others are individually made as unique pieces.

Because every detail is created with patience and care, the process often takes several days. This allows us to focus on quality, beauty, and the small details that make each candle special.

Behind every candle is time, creativity, and a love for handmade design.""",
        "body_bg": """Всяко творение започва с идея.

Преди една свещ да стигне до вашия дом, тя преминава през внимателен процес на проектиране и изработка. Обмислят се формите, подготвят се калъпите, грижливо се подбират цветовете и всеки декоративен елемент се подрежда с внимание.

Всяко изделие се изработва на ръка през множество етапи — включително отливане, оформяне, добавяне на детайли на ръка и оставяне на свещта да се стегне правилно и да придобие своя завършен вид.

Някои свещи се създават в малки серии, а други се изработват индивидуално като уникални изделия.

Тъй като всеки детайл се създава с търпение и грижа, процесът често отнема няколко дни. Това ни позволява да се съсредоточим върху качеството, красотата и малките детайли, които правят всяка свещ специална.

Зад всяка свещ стоят време, творчество и любов към ръчния дизайн.""",
        "cta_label_en": None,
        "cta_label_bg": None,
        "cta_href": None,
        "sort_order": 4,
    },
    {
        "slug": "atelier",
        "type": "text_image",
        "heading_en": "Inside Our Atelier",
        "heading_bg": "Вътре в нашето ателие",
        "subheading_en": "Where Every Candle Comes to Life",
        "subheading_bg": "Където всяка свещ оживява",
        "body_en": """Behind every creation are countless small details.

Inside our atelier, each candle is carefully brought to life by hand. From preparing materials and creating unique designs to adding decorative elements and finishing every piece, each stage receives individual attention.

Our hands are involved in every step of the process, allowing us to create candles that feel personal, distinctive, and unlike mass-produced alternatives.

Through small-batch creations and individually made pieces, The Atelier Marie celebrates the beauty of craftsmanship and the charm of handmade design.

Every candle carries a little part of the process that created it.""",
        "body_bg": """Зад всяко творение стоят безброй малки детайли.

В нашето ателие всяка свещ се създава грижливо на ръка. От подготовката на материалите и създаването на уникални дизайни до добавянето на декоративни елементи и завършването на всяко изделие — всеки етап получава индивидуално внимание.

Нашите ръце участват във всяка стъпка от процеса, което ни позволява да създаваме свещи, които усещате като лични, отличителни и различни от масово произвежданите алтернативи.

Чрез творения в малки серии и индивидуално изработени изделия, The Atelier Marie възхвалява красотата на майсторството и очарованието на ръчния дизайн.

Всяка свещ носи малка част от процеса, който я е създал.""",
        "cta_label_en": None,
        "cta_label_bg": None,
        "cta_href": None,
        "sort_order": 5,
    },
    {
        "slug": "values",
        "type": "cards",
        "heading_en": "Our Values",
        "heading_bg": "Нашите ценности",
        "subheading_en": "The Principles Behind Every Creation",
        "subheading_bg": "Принципите зад всяко творение",
        "body_en": None,
        "body_bg": None,
        "cta_label_en": None,
        "cta_label_bg": None,
        "cta_href": None,
        "sort_order": 6,
    },
    {
        "slug": "collections",
        "type": "collections",
        "heading_en": "Our Collections",
        "heading_bg": "Нашите колекции",
        "subheading_en": "Designed to Suit Every Space and Story",
        "subheading_bg": "Създадени да подхождат на всяко пространство и история",
        "body_en": None,
        "body_bg": None,
        "cta_label_en": None,
        "cta_label_bg": None,
        "cta_href": None,
        "sort_order": 7,
    },
    {
        "slug": "emotional",
        "type": "text_band",
        "heading_en": "A Little Beauty for Everyday Moments",
        "heading_bg": "Малко красота за ежедневните мигове",
        "subheading_en": "Designed to Become Part of Your Story",
        "subheading_bg": "Създадени да станат част от вашата история",
        "body_en": """We believe the most beautiful objects are the ones that create a feeling.

A candle can transform a room, add warmth to your home, and become part of the moments you want to remember.

Whether chosen as a statement piece for your own space or as a meaningful gift for someone special, every creation from The Atelier Marie is designed to bring elegance, beauty, and emotion into everyday life.

From the first idea to the final detail, each candle is made with care so it can become more than decoration — it can become a small reminder of a beautiful moment.""",
        "body_bg": """Вярваме, че най-красивите предмети са тези, които създават усещане.

Една свещ може да преобрази стаята, да добави топлина към вашия дом и да стане част от миговете, които искате да запомните.

Независимо дали е избрана като акцентно изделие за собственото ви пространство, или като значим подарък за някого специален — всяко творение от The Atelier Marie е замислено да внесе елегантност, красота и емоция в ежедневието.

От първата идея до последния детайл, всяка свещ е изработена с грижа, за да може да стане повече от декорация — да се превърне в малко напомняне за един красив миг.""",
        "cta_label_en": "Discover the collection",
        "cta_label_bg": "Открийте колекцията",
        "cta_href": "/products",
        "sort_order": 8,
    },
    {
        "slug": "custom_cta",
        "type": "cta_band",
        "heading_en": "Looking for Something Unique?",
        "heading_bg": "Търсите нещо уникално?",
        "subheading_en": None,
        "subheading_bg": None,
        "body_en": "Create a personalised candle designed especially for you — a bespoke piece for a meaningful moment, or a truly one-of-a-kind gift.",
        "body_bg": "Създайте персонализирана свещ, замислена специално за вас — изделие по поръчка за значим миг или наистина уникален подарък.",
        "cta_label_en": "Request a Custom Order",
        "cta_label_bg": "Заявете индивидуална поръчка",
        "cta_href": "/contact",
        "sort_order": 9,
    },
]


_ABOUT_ITEMS = [
    (
        "differentiators",
        "Handcrafted With Attention to Detail",
        "Ръчна изработка с внимание към детайла",
        "Every candle is individually created in our atelier. From the first design idea to the final finishing touches, every element is carefully considered.",
        "Всяка свещ се създава индивидуално в нашето ателие. От първата идея за дизайна до последните завършващи щрихи — всеки елемент е обмислен внимателно.",
        None,
        0,
    ),
    (
        "differentiators",
        "Designed as Home Décor",
        "Замислени като декор за дома",
        "Our candles are created to complement beautiful interiors and become part of your space. Whether displayed as a statement piece or enjoyed as a sensory experience, each design is made to bring elegance and personality into your home.",
        "Нашите свещи са създадени да допълват красивите интериори и да станат част от вашето пространство. Независимо дали като акцентен детайл, или като сетивно изживяване, всеки дизайн внася елегантност и характер във вашия дом.",
        None,
        1,
    ),
    (
        "differentiators",
        "A Luxury Fragrance Experience",
        "Луксозно ароматно изживяване",
        "Beautiful design deserves a beautiful scent. Our fragrances are carefully selected to create a warm and memorable atmosphere, turning everyday moments into something special.",
        "Красивият дизайн заслужава красив аромат. Нашите аромати са внимателно подбрани, за да създадат топла и запомняща се атмосфера, превръщайки ежедневните мигове в нещо специално.",
        None,
        2,
    ),
    (
        "differentiators",
        "Personalised Creations",
        "Персонализирани творения",
        "Some moments deserve something truly unique. We offer personalised designs, candle bouquets, and colour combinations for those looking for a meaningful piece created especially for them.",
        "Някои мигове заслужават нещо наистина уникално. Предлагаме персонализирани дизайни, букети от свещи и цветови комбинации за тези, които търсят значимо изделие, създадено специално за тях.",
        None,
        3,
    ),
    (
        "process",
        "Design",
        "Дизайн",
        "Every creation begins with an idea, a shape, and a vision.",
        "Всяко творение започва с идея, форма и визия.",
        None,
        0,
    ),
    (
        "process",
        "Moulds",
        "Калъпи",
        "Each shape is carefully prepared so the candle can take its intended form.",
        "Всяка форма се подготвя грижливо, за да може свещта да приеме замисления си вид.",
        None,
        1,
    ),
    (
        "process",
        "Colours",
        "Цветове",
        "Shades are selected and blended by hand to achieve the perfect tone.",
        "Нюансите се подбират и смесват на ръка, за да се постигне съвършеният тон.",
        None,
        2,
    ),
    (
        "process",
        "Handmade Details",
        "Ръчни детайли",
        "Every decorative element is carefully placed by hand.",
        "Всеки декоративен елемент се поставя внимателно на ръка.",
        None,
        3,
    ),
    (
        "process",
        "Setting",
        "Стягане",
        "Each candle is given time to set properly and develop its final appearance.",
        "На всяка свещ се дава време да се стегне правилно и да придобие завършения си вид.",
        None,
        4,
    ),
    (
        "process",
        "Finishing & Packaging",
        "Завършек и опаковане",
        "Each candle receives time and attention before leaving the atelier.",
        "Всяка свещ получава време и внимание, преди да напусне ателието.",
        None,
        5,
    ),
    (
        "values",
        "Craftsmanship",
        "Майсторство",
        "True beauty comes from attention to detail. We believe every element matters, from the overall design to the smallest finishing touch.",
        "Истинската красота идва от вниманието към детайла. Вярваме, че всеки елемент има значение — от цялостния дизайн до най-малкия завършващ щрих.",
        None,
        0,
    ),
    (
        "values",
        "Elegance",
        "Елегантност",
        "Our creations are inspired by timeless aesthetics, designed to complement your home and bring a refined sense of beauty to your surroundings.",
        "Нашите творения са вдъхновени от вечната естетика, замислени да допълват вашия дом и да внесат изтънчено усещане за красота в заобикалящата ви среда.",
        None,
        1,
    ),
    (
        "values",
        "Emotion",
        "Емоция",
        "The most meaningful objects are those connected to memories. Whether chosen for yourself or gifted to someone special, our candles are created to celebrate moments worth remembering.",
        "Най-значимите предмети са тези, свързани със спомени. Независимо дали са избрани за вас, или подарени на някого специален, нашите свещи са създадени да отбележат мигове, които си заслужава да бъдат помнени.",
        None,
        2,
    ),
    (
        "values",
        "Personal Touch",
        "Личен досег",
        "Every home and every occasion is unique. Through personalised creations, we aim to create pieces that feel truly yours.",
        "Всеки дом и всеки повод са уникални. Чрез персонализирани творения се стремим да създаваме изделия, които усещате като истински ваши.",
        None,
        3,
    ),
    (
        "collections",
        "Floral Collection",
        "Флорална колекция",
        "Romantic designs inspired by nature.",
        "Романтични дизайни, вдъхновени от природата.",
        "/products?category=floral",
        0,
    ),
    (
        "collections",
        "Sculptural Collection",
        "Скулптурна колекция",
        "Statement pieces designed to decorate your space.",
        "Акцентни изделия, създадени да украсят вашето пространство.",
        "/products?category=sculptural",
        1,
    ),
    (
        "collections",
        "Bespoke Collection",
        "Колекция по поръчка",
        "Custom creations made for meaningful moments.",
        "Творения по поръчка за значими мигове.",
        "/products?category=bespoke",
        2,
    ),
]


def _seed_about_content(conn: sqlite3.Connection) -> None:
    """Seed the editable atelier story once for fresh databases."""
    row = conn.execute("SELECT COUNT(*) AS count FROM about_sections").fetchone()
    if row["count"]:
        return

    for section in _ABOUT_SECTIONS:
        conn.execute(
            """
            INSERT INTO about_sections (
                slug, type, heading_en, heading_bg, subheading_en, subheading_bg,
                body_en, body_bg, cta_label_en, cta_label_bg, cta_href,
                image_id, sort_order, is_published, created_at, updated_at
            ) VALUES (
                :slug, :type, :heading_en, :heading_bg, :subheading_en, :subheading_bg,
                :body_en, :body_bg, :cta_label_en, :cta_label_bg, :cta_href,
                NULL, :sort_order, 1, datetime('now'), datetime('now')
            )
            """,
            section,
        )

    conn.executemany(
        """
        INSERT INTO about_items (
            section, title_en, title_bg, text_en, text_bg, image_id, link_href,
            sort_order, is_published, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, 1, datetime('now'), datetime('now'))
        """,
        _ABOUT_ITEMS,
    )


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


_ORDER_NUMBER_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _order_number_from_seed(seed: str) -> str:
    """Generate a stable AM-xxxxxx code from a seed for legacy backfills."""
    value = uuid.uuid5(uuid.NAMESPACE_URL, f"atelier-marie/order-number/{seed}").int
    chars: list[str] = []
    for _ in range(6):
        value, idx = divmod(value, len(_ORDER_NUMBER_ALPHABET))
        chars.append(_ORDER_NUMBER_ALPHABET[idx])
    return "AM-" + "".join(chars)


def _backfill_order_payment_summary(conn: sqlite3.Connection) -> None:
    """Populate payment summary fields added after the first order schema."""
    if not _table_exists(conn, "orders"):
        return

    columns = _table_columns(conn, "orders")
    required = {"internal_sequence", "order_number", "payment_return_token"}
    if not required.issubset(columns):
        return

    sequence = conn.execute(
        "SELECT COALESCE(MAX(internal_sequence), 0) FROM orders"
    ).fetchone()[0]
    rows = conn.execute(
        "SELECT id FROM orders WHERE internal_sequence IS NULL ORDER BY created_at, id"
    ).fetchall()
    for row in rows:
        sequence += 1
        conn.execute(
            "UPDATE orders SET internal_sequence = ? WHERE id = ?",
            (sequence, row["id"]),
        )

    rows = conn.execute(
        "SELECT id FROM orders WHERE order_number IS NULL OR TRIM(order_number) = '' "
        "ORDER BY internal_sequence, created_at, id"
    ).fetchall()
    for row in rows:
        for attempt in range(10):
            order_number = _order_number_from_seed(f"{row['id']}:{attempt}")
            exists = conn.execute(
                "SELECT 1 FROM orders WHERE order_number = ? AND id != ?",
                (order_number, row["id"]),
            ).fetchone()
            if exists is None:
                conn.execute(
                    "UPDATE orders SET order_number = ? WHERE id = ?",
                    (order_number, row["id"]),
                )
                break
        else:
            msg = f"Could not generate unique order_number for order {row['id']}"
            raise RuntimeError(msg)

    rows = conn.execute(
        "SELECT id FROM orders "
        "WHERE payment_return_token IS NULL OR TRIM(payment_return_token) = ''"
    ).fetchall()
    for row in rows:
        for _ in range(10):
            token = uuid.uuid4().hex
            exists = conn.execute(
                "SELECT 1 FROM orders WHERE payment_return_token = ? AND id != ?",
                (token, row["id"]),
            ).fetchone()
            if exists is None:
                conn.execute(
                    "UPDATE orders SET payment_return_token = ? WHERE id = ?",
                    (token, row["id"]),
                )
                break
        else:
            msg = f"Could not generate unique payment_return_token for order {row['id']}"
            raise RuntimeError(msg)


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
        product_image_columns = _table_columns(conn, "product_images")
        _add_column_if_missing(
            conn,
            "product_images",
            product_image_columns,
            "zoom_url",
            "zoom_url TEXT",
        )
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
        # Courier transit status + label url (speedy-integration).
        _add_column_if_missing(
            conn, "orders", order_columns, "courier_status", "courier_status TEXT"
        )
        _add_column_if_missing(conn, "orders", order_columns, "label_url", "label_url TEXT")
        _add_column_if_missing(
            conn, "orders", order_columns, "locale", "locale TEXT NOT NULL DEFAULT 'en'"
        )
        # Payment axis columns (payment-integration).
        # CHECK constraints omitted on ALTER ADD COLUMN (SQLite restriction);
        # validation happens at the Pydantic + service layers.
        _add_column_if_missing(
            conn,
            "orders",
            order_columns,
            "internal_sequence",
            "internal_sequence INTEGER",
        )
        _add_column_if_missing(
            conn,
            "orders",
            order_columns,
            "order_number",
            "order_number TEXT",
        )
        _add_column_if_missing(
            conn,
            "orders",
            order_columns,
            "payment_method",
            "payment_method TEXT NOT NULL DEFAULT 'cod'",
        )
        _add_column_if_missing(
            conn,
            "orders",
            order_columns,
            "payment_status",
            "payment_status TEXT NOT NULL DEFAULT 'cod_pending'",
        )
        _add_column_if_missing(
            conn,
            "orders",
            order_columns,
            "reserved_until",
            "reserved_until TEXT",
        )
        _add_column_if_missing(conn, "orders", order_columns, "paid_at", "paid_at TEXT")
        _add_column_if_missing(
            conn,
            "orders",
            order_columns,
            "collected_at",
            "collected_at TEXT",
        )
        _add_column_if_missing(
            conn,
            "orders",
            order_columns,
            "payment_return_token",
            "payment_return_token TEXT",
        )
        _add_column_if_missing(
            conn,
            "orders",
            order_columns,
            "stripe_checkout_session_id",
            "stripe_checkout_session_id TEXT",
        )
        _add_column_if_missing(
            conn,
            "orders",
            order_columns,
            "stripe_payment_intent_id",
            "stripe_payment_intent_id TEXT",
        )
        # Shipping price + provenance (shipping-pricing — Phase A).
        _add_column_if_missing(
            conn,
            "orders",
            order_columns,
            "shipping_cents",
            "shipping_cents INTEGER NOT NULL DEFAULT 0",
        )
        _add_column_if_missing(
            conn,
            "orders",
            order_columns,
            "shipping_price_source",
            "shipping_price_source TEXT NOT NULL DEFAULT 'live'",
        )
        _add_column_if_missing(
            conn,
            "orders",
            order_columns,
            "shipping_is_fallback",
            "shipping_is_fallback INTEGER NOT NULL DEFAULT 0",
        )
        _add_column_if_missing(
            conn,
            "orders",
            order_columns,
            "shipping_quoted_at",
            "shipping_quoted_at TEXT",
        )
        _add_column_if_missing(
            conn,
            "orders",
            order_columns,
            "analytics_consent",
            "analytics_consent INTEGER NOT NULL DEFAULT 0",
        )

    if _table_exists(conn, "promotion_campaigns"):
        campaign_columns = _table_columns(conn, "promotion_campaigns")
        _add_column_if_missing(
            conn,
            "promotion_campaigns",
            campaign_columns,
            "last_result",
            "last_result TEXT",
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
        _column_expr(columns, "safety_warnings_en"),
        _column_expr(columns, "safety_warnings_bg"),
        _column_expr(columns, "care_instructions_en"),
        _column_expr(columns, "care_instructions_bg"),
        _column_expr(columns, "materials"),
        _column_expr(columns, "days_to_craft"),
        price_expr,
        _column_expr(columns, "category"),
        _column_expr(columns, "product_type_slug", "'candles'"),
        _column_expr(columns, "category_slug"),
        _column_expr(columns, "discount_percent"),
        _column_expr(columns, "discount_starts_at"),
        _column_expr(columns, "discount_ends_at"),
        _column_expr(columns, "stock", "0"),
        _column_expr(columns, "weight_grams", "300"),
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
        # Commit first: PRAGMA foreign_keys is a no-op inside an open transaction,
        # so re-enabling enforcement only takes effect once the rebuild is committed.
        conn.commit()
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
    """Seed starter taxonomy and (once) backfill labels from legacy categories.

    The seed + backfill + marker write run inside a single BEGIN IMMEDIATE
    transaction so concurrent uvicorn workers can't both execute the one-shot
    backfill on first boot: the second worker blocks on the write lock, then
    re-checks the marker inside the lock and no-ops. The marker (not "seeds
    present") is the gate, so re-runs are a no-op even when seeds already exist.
    """
    # Fast path: already applied — avoid taking the write lock on every startup.
    if _migration_applied(conn, _TAXONOMY_MIGRATION_MARKER):
        return

    if conn.in_transaction:
        conn.commit()
    conn.execute("BEGIN IMMEDIATE")
    try:
        # Re-check under the lock: another worker may have applied it while we
        # waited to acquire the write lock.
        if _migration_applied(conn, _TAXONOMY_MIGRATION_MARKER):
            conn.execute("ROLLBACK")
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
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


# ---------------------------------------------------------------------------
# FAQ content seed migration (admin-managed-faq)
# ---------------------------------------------------------------------------

# The four stable sections. Slugs are used as public page anchors and product
# deep-link targets, so they must never change. Each entry:
# (slug, title_en, title_bg, icon, sort_order).
_SEED_FAQ_SECTIONS = [
    ("candles", "About Our Candles", "За нашите свещи", "🕯", 0),
    ("care", "Candle Care & Safety", "Грижа и безопасност", "✨", 1),
    ("custom", "Custom Orders & Gifts", "Поръчки по заявка и подаръци", "🎁", 2),
    ("shipping", "Orders, Shipping & Returns", "Поръчки, доставка и връщане", "📦", 3),
]

# Bulleted safety answer — raw plain text with `* ` markers and newlines so the
# frontend renderer emits a <ul>. Stored verbatim (not HTML-escaped).
_FAQ_SAFETY_EN = (
    "* Never leave a burning candle unattended.\n"
    "* Keep candles away from children and pets.\n"
    "* Always burn candles on a stable, heat-resistant surface.\n"
    "* Keep away from curtains, furniture, and other flammable materials.\n"
    "* Never move a candle while it is burning or while the wax is still hot.\n"
    "* Extinguish the candle before it burns completely."
)
_FAQ_SAFETY_BG = (
    "* Никога не оставяйте горяща свещ без надзор.\n"
    "* Дръжте свещите далеч от деца и домашни любимци.\n"
    "* Винаги горете свещите върху стабилна, топлоустойчива повърхност.\n"
    "* Дръжте далеч от завеси, мебели и други запалими материали.\n"
    "* Никога не местете свещ, докато гори или докато восъкът е още горещ.\n"
    "* Изгасете свещта, преди да изгори напълно."
)

# Every seeded item, in section + display order. Each entry:
# (section, question_en, question_bg, answer_en, answer_bg).
_SEED_FAQ_ITEMS = [
    (
        "candles",
        "Are your candles handmade?",
        "Ръчно изработени ли са вашите свещи?",
        "Yes. Every candle is lovingly handcrafted in our atelier, making each "
        "piece truly one of a kind. Because they are made by hand, slight "
        "variations in colour, finish, or decorative details are part of their "
        "unique charm.",
        "Да. Всяка свещ е изработена с любов на ръка в нашето ателие, което прави "
        "всяко изделие наистина уникално. Тъй като са изработени ръчно, леките "
        "разлики в цвета, финиша или декоративните детайли са част от техния "
        "неповторим чар.",
    ),
    (
        "candles",
        "What wax do you use?",
        "Какъв восък използвате?",
        "We carefully select different premium wax blends depending on the "
        "candle's design and intended performance. The exact wax type used for "
        "each candle is listed in its individual product description.",
        "Внимателно подбираме различни висококачествени восъчни смеси в "
        "зависимост от дизайна и предназначението на свещта. Точният вид восък за "
        "всяка свещ е посочен в описанието на съответния продукт.",
    ),
    (
        "candles",
        "What type of wick do you use?",
        "Какъв вид фитил използвате?",
        "We use different wick types depending on the candle's size and design to "
        "ensure the best possible performance. The wick information for each "
        "candle can be found on its product page.",
        "Използваме различни видове фитили в зависимост от размера и дизайна на "
        "свещта, за да осигурим възможно най-добро горене. Информация за фитила на "
        "всяка свещ можете да намерите на нейната продуктова страница.",
    ),
    (
        "candles",
        "Where are your candles made?",
        "Къде се произвеждат вашите свещи?",
        "All of our candles are handcrafted in our atelier with great attention "
        "to detail and quality.",
        "Всички наши свещи са изработени ръчно в нашето ателие с изключително "
        "внимание към детайла и качеството.",
    ),
    (
        "candles",
        "What sizes do you offer?",
        "Какви размери предлагате?",
        "Our collection includes candles in a variety of sizes. Please refer to "
        "each product page for the exact dimensions and weight.",
        "Нашата колекция включва свещи в различни размери. Моля, вижте всяка "
        "продуктова страница за точните размери и тегло.",
    ),
    (
        "candles",
        "What makes your candles different?",
        "Какво отличава вашите свещи?",
        "Our candles are designed to be more than just home fragrance—they're "
        "decorative pieces made to elevate your space. Combining handcrafted "
        "craftsmanship, luxurious fragrances, elegant designs, and premium "
        "materials, each candle is created to bring beauty and warmth into your "
        "home. Many of our products can also be customised, making them a "
        "thoughtful and unique gift.",
        "Нашите свещи са замислени да бъдат нещо повече от аромат за дома — те са "
        "декоративни изделия, създадени да облагородят пространството ви. "
        "Съчетавайки ръчна изработка, изискани аромати, елегантен дизайн и "
        "първокласни материали, всяка свещ е създадена да внесе красота и топлина "
        "в дома ви. Много от нашите продукти могат да бъдат персонализирани, "
        "което ги прави обмислен и уникален подарък.",
    ),
    (
        "care",
        "Are all of your candles meant to be burned?",
        "Всички ваши свещи ли са предназначени за горене?",
        "Not necessarily. Some of our candles are designed primarily as "
        "decorative pieces, while others are suitable for burning. Please check "
        "the product description before lighting your candle.",
        "Не непременно. Някои от нашите свещи са създадени предимно като "
        "декоративни изделия, докато други са подходящи за горене. Моля, "
        "проверете описанието на продукта, преди да запалите свещта си.",
    ),
    (
        "care",
        "Do I need to trim the wick before the first burn?",
        "Трябва ли да подрязвам фитила преди първото горене?",
        "No. Every candle arrives with the wick pre-trimmed and ready to light. "
        "If you burn your candle multiple times, trimming the wick before each "
        "subsequent burn will help maintain a cleaner flame.",
        "Не. Всяка свещ пристига с предварително подрязан фитил, готова за палене. "
        "Ако горите свещта многократно, подрязването на фитила преди всяко "
        "следващо палене ще помогне за по-чист пламък.",
    ),
    (
        "care",
        "How long should I burn my candle?",
        "Колко дълго да горя свещта си?",
        "Recommended burn times vary depending on the candle's size and design. "
        "Please refer to the individual product description for guidance.",
        "Препоръчителното време за горене варира в зависимост от размера и дизайна "
        "на свещта. Моля, вижте описанието на съответния продукт за насоки.",
    ),
    (
        "care",
        "Will decorative candles drip?",
        "Капят ли декоративните свещи?",
        "Yes. Sculptural candles and decorative designs naturally lose their "
        "shape as they burn and may drip wax. Always place them on a "
        "heat-resistant tray or dish large enough to catch any melted wax.",
        "Да. Скулптурните свещи и декоративните дизайни естествено губят формата "
        "си при горене и могат да капят восък. Винаги ги поставяйте върху "
        "топлоустойчива подложка или чиния, достатъчно голяма да събере "
        "разтопения восък.",
    ),
    (
        "care",
        "How should I display decorative candles?",
        "Как да излагам декоративните свещи?",
        "To preserve their appearance, keep decorative candles away from direct "
        "sunlight, radiators, or other heat sources. Prolonged exposure may cause "
        "colours to fade or change over time.",
        "За да запазите външния им вид, дръжте декоративните свещи далеч от пряка "
        "слънчева светлина, радиатори и други източници на топлина. Продължителното "
        "излагане може да доведе до избледняване или промяна на цветовете с "
        "времето.",
    ),
    (
        "care",
        "Will my candle look exactly like the photos?",
        "Ще изглежда ли свещта ми точно като на снимките?",
        "We do our best to ensure every candle closely matches the product "
        "photos. Because each piece is handmade, small variations in decorative "
        "elements—such as fruit toppings or other handcrafted details—may occur. "
        "These slight differences make every candle unique while maintaining the "
        "same overall design and colour palette.",
        "Правим всичко възможно всяка свещ да съответства максимално на "
        "продуктовите снимки. Тъй като всяко изделие е ръчно изработено, възможни "
        "са малки разлики в декоративните елементи — като плодови акценти или "
        "други ръчно изработени детайли. Тези леки разлики правят всяка свещ "
        "уникална, като запазват същия цялостен дизайн и цветова палитра.",
    ),
    (
        "care",
        "Candle Safety",
        "Безопасност при работа със свещи",
        _FAQ_SAFETY_EN,
        _FAQ_SAFETY_BG,
    ),
    (
        "custom",
        "Can I customise my candle?",
        "Мога ли да персонализирам свещта си?",
        "Yes. We love bringing our customers' ideas to life. If you have a "
        "specific design, colour palette, fragrance, or occasion in mind, we'd be "
        "delighted to discuss a custom order.",
        "Да. Обичаме да претворяваме идеите на нашите клиенти. Ако имате конкретен "
        "дизайн, цветова палитра, аромат или повод предвид, с удоволствие ще "
        "обсъдим поръчка по заявка.",
    ),
    (
        "custom",
        "Can I request a custom candle bouquet?",
        "Мога ли да поръчам персонализиран букет от свещи?",
        "Absolutely. We create personalised candle bouquets and custom colour "
        "palettes for birthdays, weddings, anniversaries, baby showers, corporate "
        "gifts, and many other special occasions.",
        "Разбира се. Създаваме персонализирани букети от свещи и индивидуални "
        "цветови палитри за рождени дни, сватби, годишнини, бебешки партита, "
        "корпоративни подаръци и много други специални поводи.",
    ),
    (
        "custom",
        "Can I include a gift message?",
        "Мога ли да добавя подаръчно съобщение?",
        "Of course. Simply leave a note with your order and send your gift "
        "message through our Contact Form. We'll include it with your order.",
        "Разбира се. Просто оставете бележка към поръчката си и изпратете "
        "подаръчното съобщение чрез нашата форма за контакт. Ще го приложим към "
        "поръчката ви.",
    ),
    (
        "custom",
        "Are your candles suitable as gifts?",
        "Подходящи ли са вашите свещи за подарък?",
        "Yes. Every candle is beautifully presented in our custom gift-ready "
        "packaging, making it perfect for gifting without the need for additional "
        "wrapping.",
        "Да. Всяка свещ е красиво представена в нашата специална подаръчна "
        "опаковка, което я прави идеална за подарък без нужда от допълнително "
        "опаковане.",
    ),
    (
        "shipping",
        "How long does it take to prepare my order?",
        "Колко време отнема подготовката на поръчката ми?",
        "Preparation times vary depending on the product and whether it is made "
        "to order. Estimated processing times are displayed on each product page "
        "and during checkout.",
        "Времето за подготовка варира в зависимост от продукта и дали е изработван "
        "по заявка. Ориентировъчните срокове за обработка са посочени на всяка "
        "продуктова страница и при плащане.",
    ),
    (
        "shipping",
        "Can I change or cancel my order?",
        "Мога ли да променя или отменя поръчката си?",
        "If your order has not yet entered production or been dispatched, we'll "
        "do our very best to accommodate your request. Please contact us as soon "
        "as possible.",
        "Ако поръчката ви все още не е влязла в производство или не е изпратена, ще "
        "направим всичко възможно да удовлетворим молбата ви. Моля, свържете се с "
        "нас възможно най-скоро.",
    ),
    (
        "shipping",
        "What should I do if my order arrives damaged?",
        "Какво да направя, ако поръчката ми пристигне повредена?",
        "We take great care when packaging every order, but if your item arrives "
        "damaged, please contact us as soon as possible through our Contact Form "
        "or by email. Include your order number along with clear photos of the "
        "item and its packaging so we can resolve the issue promptly.",
        "Опаковаме всяка поръчка с изключително внимание, но ако изделието ви "
        "пристигне повредено, моля, свържете се с нас възможно най-скоро чрез "
        "нашата форма за контакт или по имейл. Приложете номера на поръчката си "
        "заедно с ясни снимки на изделието и опаковката, за да разрешим проблема "
        "бързо.",
    ),
    (
        "shipping",
        "Do you accept returns?",
        "Приемате ли връщания?",
        "Please refer to our Terms & Conditions for full details regarding "
        "withdrawal rights, returns, exchanges, and personalised items.",
        "Моля, вижте нашите Общи условия за пълна информация относно правото "
        "на отказ, връщанията, замените и персонализираните изделия.",
    ),
    (
        "shipping",
        "How can I contact you?",
        "Как мога да се свържа с вас?",
        "You can contact us anytime through our Contact Form or by email. We aim "
        "to respond to all enquiries as quickly as possible.",
        "Можете да се свържете с нас по всяко време чрез нашата форма за контакт "
        "или по имейл. Стремим се да отговаряме на всички запитвания възможно "
        "най-бързо.",
    ),
]

_FAQ_SEED_MARKER = "faq_content_v1"
_FAQ_RETURNS_POLICY_MARKER = "faq_returns_terms_v1"

_OLD_FAQ_RETURNS_ANSWER_EN = (
    "Please refer to our Returns & Refunds Policy for full details regarding "
    "returns, exchanges, and personalised items."
)
_OLD_FAQ_RETURNS_ANSWER_BG = (
    "Моля, вижте нашата Политика за връщане и възстановяване на суми за пълна "
    "информация относно връщания, замени и персонализирани изделия."
)
_NEW_FAQ_RETURNS_ANSWER_EN = (
    "Please refer to our Terms & Conditions for full details regarding "
    "withdrawal rights, returns, exchanges, and personalised items."
)
_NEW_FAQ_RETURNS_ANSWER_BG = (
    "Моля, вижте нашите Общи условия за пълна информация относно правото "
    "на отказ, връщанията, замените и персонализираните изделия."
)


def _migrate_faq(conn: sqlite3.Connection) -> None:
    """Seed the four FAQ sections and their initial items exactly once.

    Marker-guarded (mirrors `_migrate_taxonomy`): the seed + marker write run in
    one BEGIN IMMEDIATE transaction so concurrent workers can't double-seed, and
    the marker (not "table empty") is the gate — so once seeded, edits or
    deletions of seeded rows are never re-created on later startups.
    """
    if _migration_applied(conn, _FAQ_SEED_MARKER):
        return

    if conn.in_transaction:
        conn.commit()
    conn.execute("BEGIN IMMEDIATE")
    try:
        if _migration_applied(conn, _FAQ_SEED_MARKER):
            conn.execute("ROLLBACK")
            return

        conn.executemany(
            "INSERT OR IGNORE INTO faq_sections "
            "(slug, title_en, title_bg, icon, sort_order) VALUES (?, ?, ?, ?, ?)",
            _SEED_FAQ_SECTIONS,
        )

        # sort_order is assigned per-section in list order.
        per_section_order: dict[str, int] = {}
        item_rows = []
        for section, question_en, question_bg, answer_en, answer_bg in _SEED_FAQ_ITEMS:
            order = per_section_order.get(section, 0)
            per_section_order[section] = order + 1
            item_rows.append((section, question_en, question_bg, answer_en, answer_bg, order))
        conn.executemany(
            "INSERT INTO faq_items "
            "(section, question_en, question_bg, answer_en, answer_bg, sort_order, "
            "is_published) VALUES (?, ?, ?, ?, ?, ?, 1)",
            item_rows,
        )

        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations (name) VALUES (?)",
            (_FAQ_SEED_MARKER,),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def _migrate_faq_returns_policy_reference(conn: sqlite3.Connection) -> None:
    """Point the exact old seeded returns FAQ answer at Terms & Conditions."""
    if _migration_applied(conn, _FAQ_RETURNS_POLICY_MARKER):
        return

    if conn.in_transaction:
        conn.commit()
    conn.execute("BEGIN IMMEDIATE")
    try:
        if _migration_applied(conn, _FAQ_RETURNS_POLICY_MARKER):
            conn.execute("ROLLBACK")
            return

        conn.execute(
            """
            UPDATE faq_items
            SET answer_en = ?, answer_bg = ?
            WHERE section = 'shipping'
              AND question_en = 'Do you accept returns?'
              AND question_bg = 'Приемате ли връщания?'
              AND answer_en = ?
              AND answer_bg = ?
            """,
            (
                _NEW_FAQ_RETURNS_ANSWER_EN,
                _NEW_FAQ_RETURNS_ANSWER_BG,
                _OLD_FAQ_RETURNS_ANSWER_EN,
                _OLD_FAQ_RETURNS_ANSWER_BG,
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations (name) VALUES (?)",
            (_FAQ_RETURNS_POLICY_MARKER,),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


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
