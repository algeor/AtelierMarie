# Database Schema — AtelierMarie

> SQLite (WAL mode) • All timestamps stored as ISO 8601 text • Prices in cents (integer)

---

## Entity Relationship Diagram

```
┌──────────────────────┐         ┌──────────────────────────┐
│       users          │         │        products           │
├──────────────────────┤         ├──────────────────────────┤
│ PK id          TEXT  │         │ PK id            TEXT     │
│ UK google_id   TEXT  │         │    name_en       TEXT     │
│ UK email       TEXT  │         │    name_bg       TEXT     │
│    name        TEXT  │         │    description_en TEXT    │
│    avatar_url  TEXT  │         │    description_bg TEXT    │
│    is_admin    INT   │         │    materials     TEXT     │
│    created_at  TEXT  │         │    days_to_craft INT      │
│    last_login_at TEXT│         │    price_cents   INT >0   │
└──────────┬───────────┘         │    category      TEXT     │
           │                     │    image_url     TEXT     │
           │ 1                   │    stock         INT ≥0   │
           │                     │    is_active     INT      │
           ▼ 0..N               │    is_featured   INT      │
┌──────────────────────┐         │    translation_stale_bg   │
│      sessions        │         │    translation_stale_en   │
├──────────────────────┤         │    created_at    TEXT     │
│ PK id          TEXT  │         │    updated_at    TEXT     │
│ FK user_id     TEXT ─┼── → users(id)                      │
│    preferred_locale  │         └─────────┬────────────────┘
│    created_at  TEXT  │                   │
│    expires_at  TEXT  │                   │ 1
└──────────┬───────────┘                   │
           │                               │
     ┌─────┼──────────────┐                │
     │     │              │                │
     │ 1   │ 1            │ 1             │
     ▼     ▼              ▼               │
  0..N   0..N           0..N              │
┌────────────────┐  ┌─────────────┐  ┌────┴───────────────┐
│   cart_items   │  │   orders    │  │     reactions       │
├────────────────┤  ├─────────────┤  ├────────────────────┤
│ PK session_id ─┼→ sessions(id) │  │ PK session_id TEXT  │
│ PK product_id ─┼→ products(id) │  │ PK product_id TEXT ─┼→ products(id)
│    quantity INT │  │ PK id  TEXT │  │ PK reaction_type   │
│    added_at    │  │ session_id  │  │    created_at TEXT  │
└────────────────┘  │ FK user_id ─┼→ users(id)            │
                    │ status TEXT  │  └────────────────────┘
                    │ total_cents  │
                    │ customer_*   │         ┌──────────────────────┐
                    │ shipping_*   │         │      comments        │
                    │ notes        │         ├──────────────────────┤
                    │ created_at   │         │ PK id          TEXT  │
                    │ updated_at   │         │ FK product_id  TEXT ─┼→ products(id)
                    └──────┬──────┘         │    session_id  TEXT  │
                           │                │ FK user_id     TEXT ─┼→ users(id)
                           │ 1              │    display_name TEXT │
                           ▼ 0..N           │    body        TEXT  │
                    ┌──────────────┐        │    created_at  TEXT  │
                    │ order_items  │        └──────────────────────┘
                    ├──────────────┤
                    │ PK order_id ─┼→ orders(id)
                    │ PK product_id│  (no FK — snapshot)
                    │ product_name │
                    │ price_cents  │
                    │ quantity     │
                    └──────────────┘
```

---

## Table Details

### `users`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | TEXT | **PK** | UUID4 |
| `google_id` | TEXT | UNIQUE, NOT NULL | Google OAuth subject ID |
| `email` | TEXT | UNIQUE, NOT NULL | |
| `name` | TEXT | | Display name from Google profile |
| `avatar_url` | TEXT | | Profile picture URL |
| `is_admin` | INTEGER | NOT NULL, DEFAULT 0 | First OAuth user auto-promoted |
| `created_at` | TEXT | NOT NULL, DEFAULT now | |
| `last_login_at` | TEXT | | Updated on each login |

### `sessions`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | TEXT | **PK** | UUID4 session cookie value |
| `user_id` | TEXT | **FK → users(id)** | NULL for anonymous sessions |
| `preferred_locale` | TEXT | NOT NULL, DEFAULT 'en' | 'en' or 'bg' |
| `created_at` | TEXT | NOT NULL, DEFAULT now | |
| `expires_at` | TEXT | NOT NULL | 30-day TTL; cleaned up hourly |

### `products`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | TEXT | **PK** | SKU/slug (e.g. `lavender-dream-300ml`) |
| `name_en` | TEXT | NOT NULL | English product name |
| `name_bg` | TEXT | | Bulgarian product name |
| `description_en` | TEXT | | |
| `description_bg` | TEXT | | |
| `materials` | TEXT | | Comma-separated materials list |
| `days_to_craft` | INTEGER | | Artisan crafting time |
| `price_cents` | INTEGER | NOT NULL, CHECK > 0 | Price in cents (always integer) |
| `category` | TEXT | | Product category |
| `image_url` | TEXT | | Primary product image |
| `stock` | INTEGER | NOT NULL, DEFAULT 0, CHECK ≥ 0 | Available inventory |
| `is_active` | INTEGER | NOT NULL, DEFAULT 1 | Soft-delete flag |
| `is_featured` | INTEGER | NOT NULL, DEFAULT 0 | Homepage feature flag |
| `translation_stale_bg` | INTEGER | NOT NULL, DEFAULT 0 | Translation needs update |
| `translation_stale_en` | INTEGER | NOT NULL, DEFAULT 0 | Translation needs update |
| `created_at` | TEXT | NOT NULL, DEFAULT now | |
| `updated_at` | TEXT | NOT NULL, DEFAULT now | Auto-updated via trigger |

### `cart_items`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `session_id` | TEXT | **PK**, **FK → sessions(id) ON DELETE CASCADE** | Cart belongs to session |
| `product_id` | TEXT | **PK**, **FK → products(id)** | |
| `quantity` | INTEGER | NOT NULL, DEFAULT 1, CHECK 1–99 | |
| `added_at` | TEXT | NOT NULL, DEFAULT now | |

### `orders`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | TEXT | **PK** | UUID4 |
| `session_id` | TEXT | NOT NULL | Session that placed the order |
| `user_id` | TEXT | **FK → users(id)** | NULL if placed anonymously |
| `status` | TEXT | NOT NULL, DEFAULT 'pending', CHECK IN (...) | State machine: pending → confirmed → shipped → delivered; cancel from pending/confirmed |
| `total_cents` | INTEGER | NOT NULL, CHECK ≥ 0 | Order total in cents |
| `customer_email` | TEXT | NOT NULL | |
| `customer_name` | TEXT | | |
| `shipping_address` | TEXT | | |
| `notes` | TEXT | | Customer notes |
| `created_at` | TEXT | NOT NULL, DEFAULT now | |
| `updated_at` | TEXT | NOT NULL, DEFAULT now | Auto-updated via trigger |

**Valid status transitions:**
```
pending → confirmed → shipped → delivered
pending → cancelled
confirmed → cancelled
```

### `order_items`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `order_id` | TEXT | **PK**, **FK → orders(id)** | |
| `product_id` | TEXT | **PK** | **No FK** — intentional snapshot |
| `product_name` | TEXT | NOT NULL | Name at time of purchase |
| `price_cents` | INTEGER | NOT NULL, CHECK > 0 | Price at time of purchase |
| `quantity` | INTEGER | NOT NULL, CHECK 1–99 | |

> **Design decision:** `product_id` is NOT a foreign key. Order history is immutable — even if a product is deleted, order records remain intact with the snapshot data.

### `reactions`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `session_id` | TEXT | **PK** | |
| `product_id` | TEXT | **PK**, **FK → products(id) ON DELETE CASCADE** | |
| `reaction_type` | TEXT | **PK**, CHECK IN ('heart', 'thumbs_up') | |
| `created_at` | TEXT | NOT NULL, DEFAULT now | |

### `reaction_toggle_log`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `session_id` | TEXT | NOT NULL | |
| `product_id` | TEXT | NOT NULL | |
| `toggled_at` | TEXT | NOT NULL, DEFAULT now | Rate-limit window tracking |

> Append-only table for rate-limiting reaction toggles. No PK — just inserts.

### `comments`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | TEXT | **PK** | UUID4 |
| `product_id` | TEXT | NOT NULL, **FK → products(id) ON DELETE CASCADE** | |
| `session_id` | TEXT | NOT NULL | Author's session |
| `user_id` | TEXT | **FK → users(id) ON DELETE SET NULL** | NULL if anonymous or user deleted |
| `display_name` | TEXT | NOT NULL | Sanitized display name |
| `body` | TEXT | NOT NULL | Sanitized comment body |
| `created_at` | TEXT | NOT NULL, DEFAULT now | |

---

## Dependency Graph (Foreign Keys)

```
users
  ↑
  │ (user_id)
  ├── sessions
  │     ↑
  │     │ (session_id)
  │     ├── cart_items ──→ products
  │     │
  │     └── (session_id referenced in orders, reactions, comments — some without FK)
  │
  ├── orders
  │     ↑
  │     │ (order_id)
  │     └── order_items   (product_id is NOT an FK — snapshot)
  │
  └── comments ──→ products

products
  ↑
  │ (product_id)
  ├── cart_items
  ├── reactions
  ├── comments
  └── (order_items — logical reference, no FK)
```

### Cascade Behavior

| FK Relationship | ON DELETE |
|-----------------|-----------|
| sessions.user_id → users | _(no action — default RESTRICT)_ |
| cart_items.session_id → sessions | **CASCADE** |
| cart_items.product_id → products | _(no action)_ |
| orders.user_id → users | _(no action)_ |
| order_items.order_id → orders | _(no action)_ |
| reactions.product_id → products | **CASCADE** |
| comments.product_id → products | **CASCADE** |
| comments.user_id → users | **SET NULL** |

---

## Full-Text Search (FTS5)

Two virtual tables for bilingual product search:

| Virtual Table | Indexed Columns | Content Source |
|---------------|-----------------|----------------|
| `products_fts_en` | name_en, description_en, category | products (content-synced) |
| `products_fts_bg` | name_bg, description_bg, category | products (content-synced) |

Kept in sync via 6 triggers (INSERT/UPDATE/DELETE × 2 languages) that mirror changes from `products` into the FTS tables.

---

## Indexes

| Index | Table | Columns | Purpose |
|-------|-------|---------|---------|
| `idx_sessions_expires_at` | sessions | expires_at | Hourly cleanup query |
| `idx_cart_items_session_id` | cart_items | session_id | Cart lookup by session |
| `idx_orders_session_id` | orders | session_id | Order history by session |
| `idx_orders_user_id` | orders | user_id | Order history by user |
| `idx_orders_status` | orders | status | Admin order filtering |
| `idx_products_category` | products | category | Category browse |
| `idx_products_is_active` | products | is_active | Active product listing |
| `idx_reactions_product_type` | reactions | product_id, reaction_type | Reaction count aggregation |
| `idx_reactions_session_created` | reactions | session_id, created_at | Rate-limit checks |
| `idx_reaction_toggle_log_session_time` | reaction_toggle_log | session_id, toggled_at | Rate-limit window |
| `idx_comments_product_created` | comments | product_id, created_at | Comment thread listing |
| `idx_comments_session_created` | comments | session_id, created_at | Per-session rate-limit |

---

## Auto-Update Triggers

| Trigger | Table | Action |
|---------|-------|--------|
| `products_updated_at` | products | Sets `updated_at = now` on any UPDATE |
| `orders_updated_at` | orders | Sets `updated_at = now` on any UPDATE |
