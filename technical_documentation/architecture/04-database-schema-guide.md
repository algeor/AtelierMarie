# Database Schema Guide

This is the human map. For exact columns, use `docs/DATABASE_SCHEMA.md` and `app/database.py`.

## Storage Rules

- Main database: Postgres (via `DATABASE_URL`).
- Schema source: Alembic migrations (`alembic upgrade head`). No runtime schema creation.
- Foreign keys: always enforced (native Postgres, no PRAGMA).
- Timestamps: `timestamptz`, default `CURRENT_TIMESTAMP`; pooled connections run in UTC.
- Money: integer cents.
- Booleans: integers `0` or `1` (SQLite-compatible flag semantics kept, with `CHECK (col IN (0,1))`).
- JSON: text blobs where structure is flexible, for example delivery details.
- `updated_at`: maintained by the shared `set_updated_at()` trigger function.
- Analytics reports: separate DuckDB file when enabled.

## Core Table Groups

### Product catalog

Tables:

- `products`
- `product_types`
- `product_categories`
- `product_labels`
- `product_label_assignments`

What to remember:

- `products.id` is text.
- Bilingual product fields live on `products`.
- Managed taxonomy uses slugs.
- Legacy `category` remains for compatibility.
- Product search uses expression GIN indexes (`idx_products_search_en`/`_bg`) over `to_tsvector('simple', ...)`, not FTS tables.

### Product media

Tables:

- `product_images`
- `product_videos`

What to remember:

- Product images are many-to-one.
- One primary image per product is enforced by a partial unique index.
- Video is one-to-one by product.
- Video status is constrained to queue states.

### Identity and cart

Tables:

- `users`
- `sessions`
- `analytics_consents`
- `cart_items`

What to remember:

- Anonymous session comes first.
- `sessions.user_id` links login to session.
- Cart is session-keyed.
- Consent is session-keyed and versioned.

### Orders and payments

Tables:

- `orders`
- `order_items`
- `stripe_events`

What to remember:

- `orders.status` is fulfillment state.
- `orders.payment_status` is money state.
- `order_items` intentionally has no FK to products. It is a purchase snapshot.
- `stripe_events` is webhook dedup.

### Email and contact

Tables:

- `order_emails`
- `order_email_send_claims`
- `suppressed_emails`
- `contact_messages`

What to remember:

- `order_emails` is an outbox and audit trail.
- A partial unique index prevents more than one successful send per order/event.
- Claims coordinate workers.
- Suppression protects against re-contacting bounced/complaining recipients.

### Social proof

Tables:

- `reactions`
- `reaction_toggle_log`
- `comments`

What to remember:

- Reactions are session-scoped.
- Toggle log supports rate limiting.
- Comments can include free text, so sanitize and moderate.

### Promotions and content

Tables:

- `promotion_campaigns`
- `promotion_campaign_products`
- `site_banners`
- `faq_sections`
- `faq_items`
- `about_sections`
- `about_items`
- `delivery_settings`

What to remember:

- Campaign rows manage product discount fields. Runtime pricing reads products.
- Banner is a singleton-style row.
- FAQ/about content follows bilingual field patterns.
- Delivery settings control which courier/method pairs are usable.

## Migration Style

The project uses Alembic. The schema lives entirely in migration scripts under `alembic/versions/`; `alembic upgrade head` builds it. The app verifies the DB is at head on startup and fails fast otherwise.

Rules for schema changes:

- Add a new Alembic revision; never mutate schema at runtime.
- Provide a working `downgrade` where practical.
- Fresh DB (`alembic upgrade head` from empty) must yield the final desired schema and seed rows.
- Backfills must be idempotent.
- Tests should cover fresh-DB creation and schema-head validation.

## Dangerous Tables

Be extra careful with:

- `orders`: money, fulfillment, payment, shipping, PII.
- `order_items`: historical snapshots.
- `products`: stock, price, active flags.
- `cart_items`: session cart and quantity limits.
- `order_emails`: idempotent sending and audit.
- `sessions`: auth/cart continuity.

