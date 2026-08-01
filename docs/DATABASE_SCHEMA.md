# Database Schema - AtelierMarie

Refreshed: 2026-07-31

This document reflects the current schema created by `app.database.init_db()` plus
the first-party analytics DuckDB schema from `app.services.analytics_service`.

Verification used:

- `app/database.py` (`_SCHEMA_SQL` and startup migrations)
- a fresh temporary SQLite database initialized through `init_db()`
- the local `./atelier_marie.db` catalog, compared read-only against fresh schema
- `analytics-data/analytics.duckdb`, inspected with `uv run python`

## Storage Rules

- Main app database: SQLite at `DATABASE_PATH`, default `./atelier_marie.db`.
- SQLite startup enables `PRAGMA journal_mode=WAL` and `PRAGMA foreign_keys=ON`.
- Timestamps are stored as text from `datetime('now')` unless supplied by code.
- Money values are integer cents.
- Boolean values are integers constrained to `0` or `1` where the fresh schema has
  a check constraint.
- JSON payloads are stored in `TEXT` columns.
- Analytics storage is separate DuckDB at `ANALYTICS_DUCKDB_PATH`, default
  `./analytics-data/analytics.duckdb`.

## Main SQLite Tables

### Products And Taxonomy

`products`

| Column | Type | Constraints / notes |
|---|---:|---|
| `id` | TEXT | Primary key |
| `name_en` | TEXT | Not null |
| `name_bg` | TEXT | Nullable |
| `description_en` | TEXT | Nullable |
| `description_bg` | TEXT | Nullable |
| `safety_warnings_en` | TEXT | Nullable |
| `safety_warnings_bg` | TEXT | Nullable |
| `care_instructions_en` | TEXT | Nullable |
| `care_instructions_bg` | TEXT | Nullable |
| `materials` | TEXT | Nullable |
| `days_to_craft` | INTEGER | Nullable |
| `price_cents` | INTEGER | Not null, `CHECK (price_cents > 0)` |
| `category` | TEXT | Legacy free-text category, kept for compatibility |
| `product_type_slug` | TEXT | Not null, default `'candles'`; logical taxonomy key, no DB FK |
| `category_slug` | TEXT | Nullable; logical taxonomy key, no DB FK |
| `discount_percent` | INTEGER | Nullable, `1..99` when present |
| `discount_starts_at` | TEXT | Nullable |
| `discount_ends_at` | TEXT | Nullable |
| `stock` | INTEGER | Not null, default `0`, `CHECK (stock >= 0)` |
| `weight_grams` | INTEGER | Not null, default `300`, `CHECK (weight_grams > 0)` |
| `is_active` | INTEGER | Not null, default `1` |
| `is_featured` | INTEGER | Not null, default `0` |
| `translation_stale_bg` | INTEGER | Not null, default `0` |
| `translation_stale_en` | INTEGER | Not null, default `0` |
| `created_at` | TEXT | Not null, default `datetime('now')` |
| `updated_at` | TEXT | Not null, default `datetime('now')`; trigger maintained |

`product_types`, `product_categories`, `product_labels`

These three tables share the same shape:

| Column | Type | Constraints / notes |
|---|---:|---|
| `slug` | TEXT | Primary key |
| `name_en` | TEXT | Not null |
| `name_bg` | TEXT | Nullable |
| `sort_order` | INTEGER | Not null, default `0` |
| `is_active` | INTEGER | Not null, default `1` |
| `created_at` | TEXT | Not null, default `datetime('now')` |
| `updated_at` | TEXT | Not null, default `datetime('now')` |

`product_label_assignments`

| Column | Type | Constraints / notes |
|---|---:|---|
| `product_id` | TEXT | PK part, FK -> `products(id)` `ON DELETE CASCADE` |
| `label_slug` | TEXT | PK part, FK -> `product_labels(slug)` `ON DELETE RESTRICT` |

`schema_migrations`

| Column | Type | Constraints / notes |
|---|---:|---|
| `name` | TEXT | Primary key |
| `applied_at` | TEXT | Not null, default `datetime('now')` |

`taxonomy_category_migration`

| Column | Type | Constraints / notes |
|---|---:|---|
| `original_value` | TEXT | Primary key |
| `label_slug` | TEXT | Not null |

### Product Media

`product_images`

| Column | Type | Constraints / notes |
|---|---:|---|
| `id` | TEXT | Primary key |
| `product_id` | TEXT | Not null, FK -> `products(id)` `ON DELETE CASCADE` |
| `image_url` | TEXT | Not null |
| `thumbnail_url` | TEXT | Not null |
| `zoom_url` | TEXT | Nullable |
| `sort_order` | INTEGER | Not null, default `0` |
| `is_primary` | INTEGER | Not null, default `0`, `CHECK (is_primary IN (0, 1))` |
| `created_at` | TEXT | Not null, default `datetime('now')` |

`product_videos`

| Column | Type | Constraints / notes |
|---|---:|---|
| `id` | TEXT | Primary key |
| `product_id` | TEXT | Not null, unique, FK -> `products(id)` `ON DELETE CASCADE` |
| `status` | TEXT | Not null, one of `queued`, `transcoding`, `ready`, `failed` |
| `source_path` | TEXT | Nullable |
| `video_url` | TEXT | Nullable |
| `poster_url` | TEXT | Nullable |
| `duration_secs` | REAL | Nullable |
| `sort_order` | INTEGER | Not null, default `0` |
| `failure_reason` | TEXT | Nullable |
| `lease_expires_at` | TEXT | Nullable |
| `created_at` | TEXT | Not null, default `datetime('now')` |
| `updated_at` | TEXT | Not null, default `datetime('now')`; trigger maintained |

### Identity, Sessions, And Cart

`users`

| Column | Type | Constraints / notes |
|---|---:|---|
| `id` | TEXT | Primary key |
| `google_id` | TEXT | Unique, not null |
| `email` | TEXT | Unique, not null |
| `name` | TEXT | Nullable |
| `avatar_url` | TEXT | Nullable |
| `is_admin` | INTEGER | Not null, default `0` |
| `created_at` | TEXT | Not null, default `datetime('now')` |
| `last_login_at` | TEXT | Nullable |

`sessions`

| Column | Type | Constraints / notes |
|---|---:|---|
| `id` | TEXT | Primary key |
| `user_id` | TEXT | FK -> `users(id)` |
| `preferred_locale` | TEXT | Not null, default `'en'` |
| `created_at` | TEXT | Not null, default `datetime('now')` |
| `expires_at` | TEXT | Not null |

`analytics_consents`

| Column | Type | Constraints / notes |
|---|---:|---|
| `session_id` | TEXT | Primary key, FK -> `sessions(id)` `ON DELETE CASCADE` |
| `analytics` | INTEGER | Not null, `CHECK (analytics IN (0, 1))` |
| `consent_version` | TEXT | Not null |
| `locale` | TEXT | Not null, default `'en'`, one of `en`, `bg` |
| `updated_at` | TEXT | Not null, default `datetime('now')` |

`cart_items`

| Column | Type | Constraints / notes |
|---|---:|---|
| `session_id` | TEXT | PK part, FK -> `sessions(id)` `ON DELETE CASCADE` |
| `product_id` | TEXT | PK part, FK -> `products(id)` |
| `quantity` | INTEGER | Not null, default `1`, fresh DB check `1..10` |
| `added_at` | TEXT | Not null, default `datetime('now')` |

Note: older existing DBs may still allow cart quantity up to `99`; fresh DBs
enforce the current config limit of `10`.

### Orders, Payment, And Email

`orders`

| Column | Type | Constraints / notes |
|---|---:|---|
| `id` | TEXT | Primary key |
| `session_id` | TEXT | Not null; no DB FK |
| `user_id` | TEXT | FK -> `users(id)` |
| `status` | TEXT | Not null, default `pending`; one of `pending`, `confirmed`, `shipped`, `delivered`, `return_in_transit`, `returned`, `cancelled` |
| `total_cents` | INTEGER | Not null, `CHECK (total_cents >= 0)` |
| `customer_email` | TEXT | Not null |
| `customer_name` | TEXT | Nullable |
| `shipping_cents` | INTEGER | Not null, default `0`, `CHECK (shipping_cents >= 0)` |
| `shipping_price_source` | TEXT | Not null, default `'live'` |
| `shipping_is_fallback` | INTEGER | Not null, default `0` |
| `shipping_quoted_at` | TEXT | Nullable |
| `delivery_method` | TEXT | Nullable; one of `office`, `door` on fresh DB |
| `delivery_courier` | TEXT | Nullable; one of `speedy`, `econt` on fresh DB |
| `delivery_details` | TEXT | Nullable JSON blob |
| `tracking_number` | TEXT | Nullable |
| `tracking_carrier` | TEXT | Nullable |
| `tracking_url` | TEXT | Nullable |
| `courier_status` | TEXT | Nullable |
| `label_url` | TEXT | Nullable |
| `courier_provider` | TEXT | Nullable; one of `speedy`, `econt` on fresh DB |
| `courier_order_id` | TEXT | Nullable remote courier order id |
| `courier_shipment_number` | TEXT | Nullable courier shipment/waybill number |
| `courier_label_url` | TEXT | Nullable label URL when courier returns one |
| `courier_label_created_at` | TEXT | Nullable |
| `courier_sync_status` | TEXT | Nullable admin/courier sync marker |
| `courier_last_error` | TEXT | Nullable redacted JSON/string error snapshot |
| `courier_last_synced_at` | TEXT | Nullable |
| `courier_last_polled_at` | TEXT | Nullable |
| `courier_next_poll_at` | TEXT | Nullable |
| `courier_poll_attempts` | INTEGER | Not null, default `0`, `CHECK (courier_poll_attempts >= 0)` |
| `courier_poll_lease_token` | TEXT | Nullable |
| `courier_poll_lease_expires_at` | TEXT | Nullable |
| `locale` | TEXT | Not null, default `'en'` |
| `notes` | TEXT | Nullable |
| `payment_method` | TEXT | Not null, default `cod`; one of `cod`, `card`, `bank_transfer` on fresh DB |
| `payment_status` | TEXT | Not null, default `cod_pending`; one of `pending`, `paid`, `cod_pending`, `failed`, `refunded` on fresh DB |
| `stripe_checkout_session_id` | TEXT | Nullable |
| `stripe_payment_intent_id` | TEXT | Nullable |
| `analytics_consent` | INTEGER | Not null, default `0`, `CHECK (analytics_consent IN (0, 1))` |
| `created_at` | TEXT | Not null, default `datetime('now')` |
| `updated_at` | TEXT | Not null, default `datetime('now')`; trigger maintained |

Note: several `orders` columns are migration-added on older DBs, so existing DBs
can have fewer DB-level check constraints than a fresh DB. Service and Pydantic
validation still enforce the contract.

`order_items`

| Column | Type | Constraints / notes |
|---|---:|---|
| `order_id` | TEXT | PK part, FK -> `orders(id)` |
| `product_id` | TEXT | PK part; intentionally no FK, snapshot at purchase time |
| `product_name` | TEXT | Not null |
| `price_cents` | INTEGER | Not null, `CHECK (price_cents > 0)` |
| `quantity` | INTEGER | Not null, `CHECK (quantity >= 1 AND quantity <= 99)` |

`stripe_events`

| Column | Type | Constraints / notes |
|---|---:|---|
| `event_id` | TEXT | Primary key, Stripe webhook dedup key |
| `order_id` | TEXT | Nullable, no DB FK |
| `event_type` | TEXT | Not null |
| `received_at` | TEXT | Not null |

`order_emails`

| Column | Type | Constraints / notes |
|---|---:|---|
| `id` | INTEGER | Primary key autoincrement |
| `order_id` | TEXT | Not null, FK -> `orders(id)` |
| `event` | TEXT | Not null; e.g. placed, shipped, delivered, cancelled, admin_new_order |
| `recipient` | TEXT | Not null |
| `status` | TEXT | Not null; queue/send/skip state |
| `reason` | TEXT | Nullable |
| `attempts` | INTEGER | Not null, default `0` |
| `next_attempt_at` | TEXT | Nullable |
| `sent_at` | TEXT | Not null, default `datetime('now')` |

`order_email_send_claims`

| Column | Type | Constraints / notes |
|---|---:|---|
| `order_id` | TEXT | PK part, FK -> `orders(id)` |
| `event` | TEXT | PK part |
| `status` | TEXT | Not null; `in_flight`, `sent`, or `failed` |
| `lease_expires_at` | TEXT | Nullable |
| `updated_at` | TEXT | Not null, default `datetime('now')` |

`suppressed_emails`

| Column | Type | Constraints / notes |
|---|---:|---|
| `email` | TEXT | Primary key |
| `reason` | TEXT | Not null; hard bounce, soft bounce, or complaint reason |
| `suppressed_at` | TEXT | Not null, default `datetime('now')` |

### Contact, Social, And Promotions

`contact_messages`

| Column | Type | Constraints / notes |
|---|---:|---|
| `id` | INTEGER | Primary key autoincrement |
| `name` | TEXT | Not null, length `1..100` |
| `email` | TEXT | Not null, length `3..254` |
| `message` | TEXT | Not null, length `1..2000` |
| `locale` | TEXT | Not null, default `'en'`, one of `en`, `bg` |
| `ip_address` | TEXT | Nullable |
| `email_status` | TEXT | Not null, default `queued`; queue/send terminal state |
| `email_attempts` | INTEGER | Not null, default `0`, `CHECK (email_attempts >= 0)` |
| `email_next_attempt_at` | TEXT | Nullable |
| `email_claimed_until` | TEXT | Nullable |
| `email_sent_at` | TEXT | Nullable |
| `email_error` | TEXT | Nullable |
| `created_at` | TEXT | Not null, default `datetime('now')` |

`reactions`

| Column | Type | Constraints / notes |
|---|---:|---|
| `session_id` | TEXT | PK part; no DB FK |
| `product_id` | TEXT | PK part, FK -> `products(id)` `ON DELETE CASCADE` |
| `reaction_type` | TEXT | PK part, one of `heart`, `thumbs_up` |
| `created_at` | TEXT | Not null, default `datetime('now')` |

`reaction_toggle_log`

| Column | Type | Constraints / notes |
|---|---:|---|
| `session_id` | TEXT | Not null |
| `product_id` | TEXT | Not null |
| `toggled_at` | TEXT | Not null, default `datetime('now')` |

`comments`

| Column | Type | Constraints / notes |
|---|---:|---|
| `id` | TEXT | Primary key |
| `product_id` | TEXT | Not null, FK -> `products(id)` `ON DELETE CASCADE` |
| `session_id` | TEXT | Not null; no DB FK |
| `user_id` | TEXT | FK -> `users(id)` `ON DELETE SET NULL` |
| `display_name` | TEXT | Not null |
| `body` | TEXT | Not null |
| `created_at` | TEXT | Not null, default `datetime('now')` |

`promotion_campaigns`

| Column | Type | Constraints / notes |
|---|---:|---|
| `id` | TEXT | Primary key |
| `name` | TEXT | Not null |
| `note` | TEXT | Nullable |
| `discount_percent` | INTEGER | Not null, `CHECK (discount_percent BETWEEN 1 AND 99)` |
| `discount_starts_at` | TEXT | Nullable |
| `discount_ends_at` | TEXT | Nullable |
| `target_type` | TEXT | Not null, one of `ids`, `filter` |
| `target_ids` | TEXT | Nullable JSON array when `target_type = 'ids'` |
| `target_filter` | TEXT | Nullable JSON filter when `target_type = 'filter'` |
| `applied_at` | TEXT | Nullable |
| `removed_at` | TEXT | Nullable |
| `last_result` | TEXT | Nullable JSON summary |
| `created_at` | TEXT | Not null, default `datetime('now')` |
| `updated_at` | TEXT | Not null, default `datetime('now')` |

`promotion_campaign_products`

| Column | Type | Constraints / notes |
|---|---:|---|
| `campaign_id` | TEXT | PK part, FK -> `promotion_campaigns(id)` `ON DELETE CASCADE` |
| `product_id` | TEXT | PK part; no DB FK |
| `applied_percent` | INTEGER | Nullable |
| `applied_starts_at` | TEXT | Nullable |
| `applied_ends_at` | TEXT | Nullable |

### Managed Content And Settings

`site_banners`

| Column | Type | Constraints / notes |
|---|---:|---|
| `id` | TEXT | Primary key, default `'default'` |
| `message_en` | TEXT | Nullable |
| `message_bg` | TEXT | Nullable |
| `link_label_en` | TEXT | Nullable |
| `link_label_bg` | TEXT | Nullable |
| `link_url` | TEXT | Nullable |
| `is_enabled` | INTEGER | Not null, default `0`, `CHECK (is_enabled IN (0, 1))` |
| `starts_at` | TEXT | Nullable |
| `ends_at` | TEXT | Nullable |
| `version` | INTEGER | Not null, default `1` |
| `updated_at` | TEXT | Not null, default `datetime('now')` |

`delivery_settings`

| Column | Type | Constraints / notes |
|---|---:|---|
| `id` | TEXT | Primary key, default `'default'` |
| `speedy_office_enabled` | INTEGER | Not null, default `1`, boolean check |
| `speedy_door_enabled` | INTEGER | Not null, default `1`, boolean check |
| `econt_office_enabled` | INTEGER | Not null, default `1`, boolean check |
| `econt_door_enabled` | INTEGER | Not null, default `1`, boolean check |
| `updated_at` | TEXT | Not null, default `datetime('now')`; trigger maintained |

`site_settings`

| Column | Type | Constraints / notes |
|---|---:|---|
| `key` | TEXT | Primary key |
| `value` | TEXT | Not null JSON/string payload |
| `value_type` | TEXT | Not null, default `json` |
| `is_public` | INTEGER | Not null, default `0`, boolean check |
| `updated_at` | TEXT | Not null, default `datetime('now')`; trigger maintained |

Current Speedy admin keys:

- `speedy_admin_health`: safe last health check metadata.
- `speedy_office_refresh_status`: optional DB-backed office refresh status override.

`site_setting_events`

| Column | Type | Constraints / notes |
|---|---:|---|
| `id` | INTEGER | Primary key autoincrement |
| `setting_key` | TEXT | Not null |
| `old_value` | TEXT | Nullable |
| `new_value` | TEXT | Not null |
| `admin_id` | TEXT | Nullable |
| `admin_email` | TEXT | Nullable |
| `request_id` | TEXT | Nullable |
| `created_at` | TEXT | Not null, default `datetime('now')` |

`faq_sections`

| Column | Type | Constraints / notes |
|---|---:|---|
| `slug` | TEXT | Primary key |
| `title_en` | TEXT | Not null |
| `title_bg` | TEXT | Nullable |
| `icon` | TEXT | Nullable |
| `sort_order` | INTEGER | Not null, default `0` |
| `created_at` | TEXT | Not null, default `datetime('now')` |
| `updated_at` | TEXT | Not null, default `datetime('now')`; trigger maintained |

`faq_items`

| Column | Type | Constraints / notes |
|---|---:|---|
| `id` | INTEGER | Primary key autoincrement |
| `section` | TEXT | Not null, FK -> `faq_sections(slug)` |
| `question_en` | TEXT | Not null |
| `question_bg` | TEXT | Nullable |
| `answer_en` | TEXT | Not null |
| `answer_bg` | TEXT | Nullable |
| `sort_order` | INTEGER | Not null, default `0` |
| `is_published` | INTEGER | Not null, default `1` |
| `created_at` | TEXT | Not null, default `datetime('now')` |
| `updated_at` | TEXT | Not null, default `datetime('now')`; trigger maintained |

`about_sections`

| Column | Type | Constraints / notes |
|---|---:|---|
| `slug` | TEXT | Primary key |
| `type` | TEXT | Not null |
| `heading_en` | TEXT | Not null |
| `heading_bg` | TEXT | Nullable |
| `subheading_en` | TEXT | Nullable |
| `subheading_bg` | TEXT | Nullable |
| `body_en` | TEXT | Nullable |
| `body_bg` | TEXT | Nullable |
| `cta_label_en` | TEXT | Nullable |
| `cta_label_bg` | TEXT | Nullable |
| `cta_href` | TEXT | Nullable |
| `image_id` | TEXT | Nullable |
| `sort_order` | INTEGER | Not null, default `0` |
| `is_published` | INTEGER | Not null, default `1`, boolean check |
| `created_at` | TEXT | Not null, default `datetime('now')` |
| `updated_at` | TEXT | Not null, default `datetime('now')` |

`about_items`

| Column | Type | Constraints / notes |
|---|---:|---|
| `id` | INTEGER | Primary key autoincrement |
| `section` | TEXT | Not null, FK -> `about_sections(slug)` `ON DELETE CASCADE` |
| `title_en` | TEXT | Not null |
| `title_bg` | TEXT | Nullable |
| `text_en` | TEXT | Nullable |
| `text_bg` | TEXT | Nullable |
| `image_id` | TEXT | Nullable |
| `link_href` | TEXT | Nullable |
| `sort_order` | INTEGER | Not null, default `0` |
| `is_published` | INTEGER | Not null, default `1`, boolean check |
| `created_at` | TEXT | Not null, default `datetime('now')` |
| `updated_at` | TEXT | Not null, default `datetime('now')` |

## Full-Text Search

Fresh schema creates two content-backed FTS5 virtual tables:

| Virtual table | Indexed columns | Content table |
|---|---|---|
| `products_fts_en` | `name_en`, `description_en` | `products` |
| `products_fts_bg` | `name_bg`, `description_bg` | `products` |

SQLite also creates internal FTS shadow tables, such as
`products_fts_en_data`, `products_fts_en_idx`, `products_fts_bg_data`, and
similar. Treat those as SQLite internals, not app-owned tables.

FTS sync triggers:

- `products_fts_en_insert`, `products_fts_en_update`, `products_fts_en_delete`
- `products_fts_bg_insert`, `products_fts_bg_update`, `products_fts_bg_delete`

## Indexes

| Index | Table | Columns / predicate |
|---|---|---|
| `idx_about_items_section_order` | `about_items` | `(section, sort_order)` |
| `idx_analytics_consents_current` | `analytics_consents` | `(session_id, consent_version, analytics)` |
| `idx_cart_items_session_id` | `cart_items` | `(session_id)` |
| `idx_comments_product_created` | `comments` | `(product_id, created_at)` |
| `idx_comments_session_created` | `comments` | `(session_id, created_at)` |
| `idx_contact_messages_created_at` | `contact_messages` | `(created_at)` |
| `idx_contact_messages_email_status` | `contact_messages` | `(email_status, email_next_attempt_at)` |
| `idx_contact_messages_ip_created` | `contact_messages` | `(ip_address, created_at)` |
| `idx_faq_items_section_order` | `faq_items` | `(section, sort_order)` |
| `idx_label_assignments_label` | `product_label_assignments` | `(label_slug)` |
| `idx_order_emails_order_id` | `order_emails` | `(order_id)` |
| `idx_order_emails_sent_unique` | `order_emails` | unique `(order_id, event)` where `status = 'sent'` |
| `idx_orders_session_id` | `orders` | `(session_id)` |
| `idx_orders_status` | `orders` | `(status)` |
| `idx_orders_user_id` | `orders` | `(user_id)` |
| `idx_product_images_one_primary` | `product_images` | unique `(product_id)` where `is_primary = 1` |
| `idx_product_images_product` | `product_images` | `(product_id, sort_order)` |
| `idx_product_videos_status` | `product_videos` | `(status)` |
| `idx_products_category` | `products` | `(category)` |
| `idx_products_category_slug` | `products` | `(category_slug)` |
| `idx_products_is_active` | `products` | `(is_active)` |
| `idx_products_type_slug` | `products` | `(product_type_slug)` |
| `idx_promotion_campaign_products_product` | `promotion_campaign_products` | `(product_id)` |
| `idx_promotion_campaigns_created` | `promotion_campaigns` | `(created_at)` |
| `idx_reaction_toggle_log_session_time` | `reaction_toggle_log` | `(session_id, toggled_at)` |
| `idx_reactions_product_type` | `reactions` | `(product_id, reaction_type)` |
| `idx_reactions_session_created` | `reactions` | `(session_id, created_at)` |
| `idx_sessions_expires_at` | `sessions` | `(expires_at)` |

## Updated-At Triggers

| Trigger | Table | Effect |
|---|---|---|
| `products_updated_at` | `products` | sets `updated_at = datetime('now')` after update |
| `product_videos_updated_at` | `product_videos` | sets `updated_at = datetime('now')` after update |
| `orders_updated_at` | `orders` | sets `updated_at = datetime('now')` after update |
| `delivery_settings_updated_at` | `delivery_settings` | sets `updated_at = datetime('now')` after update |
| `faq_sections_updated_at` | `faq_sections` | sets `updated_at = datetime('now')` after update |
| `faq_items_updated_at` | `faq_items` | sets `updated_at = datetime('now')` after update |

## Foreign Key Summary

| From | To | Delete behavior |
|---|---|---|
| `product_label_assignments.product_id` | `products.id` | Cascade |
| `product_label_assignments.label_slug` | `product_labels.slug` | Restrict |
| `product_images.product_id` | `products.id` | Cascade |
| `product_videos.product_id` | `products.id` | Cascade |
| `sessions.user_id` | `users.id` | No action |
| `analytics_consents.session_id` | `sessions.id` | Cascade |
| `cart_items.session_id` | `sessions.id` | Cascade |
| `cart_items.product_id` | `products.id` | No action |
| `orders.user_id` | `users.id` | No action |
| `order_items.order_id` | `orders.id` | No action |
| `order_emails.order_id` | `orders.id` | No action |
| `order_email_send_claims.order_id` | `orders.id` | No action |
| `reactions.product_id` | `products.id` | Cascade |
| `comments.product_id` | `products.id` | Cascade |
| `comments.user_id` | `users.id` | Set null |
| `promotion_campaign_products.campaign_id` | `promotion_campaigns.id` | Cascade |
| `faq_items.section` | `faq_sections.slug` | No action |
| `about_items.section` | `about_sections.slug` | Cascade |

Intentional non-FKs:

- `orders.session_id`: session snapshot, indexed but not constrained.
- `order_items.product_id`: immutable product snapshot.
- `promotion_campaign_products.product_id`: resolved target snapshot.
- `products.product_type_slug` and `products.category_slug`: logical taxonomy slugs,
  validated by service code rather than DB FKs.
- `stripe_events.order_id`: nullable webhook mapping.

## Startup Migrations And Seeds

`init_db()` does more than `CREATE TABLE IF NOT EXISTS`:

- Rebuilds legacy `products` tables into the current bilingual/safety/taxonomy
  shape when columns differ.
- Migrates old `products.image_url` into `product_images` and derives thumbnails.
- Adds migration-era columns to existing `sessions`, `orders`, `product_images`,
  and `promotion_campaigns` tables.
- Rebuilds `product_label_assignments` if the label FK is missing.
- Drops old product FTS tables/triggers and recreates the current bilingual FTS.
- Seeds starter taxonomy, FAQ content, the singleton site banner, the singleton
  delivery settings row, and editable about-page content.

Marker rows currently used in `schema_migrations` include:

- `dynamic_categories_v1`
- `faq_content_v1`
- `faq_returns_terms_v1`

## Analytics DuckDB

Created by `analytics_service.initialize_storage()` when analytics storage is
initialized.

`analytics_events`

| Column | Type | Nullability / notes |
|---|---:|---|
| `event_id` | VARCHAR | Not null |
| `session_id` | VARCHAR | Not null |
| `user_id` | VARCHAR | Nullable |
| `event_type` | VARCHAR | Not null |
| `occurred_at` | TIMESTAMP | Not null |
| `received_at` | TIMESTAMP | Not null |
| `locale` | VARCHAR | Not null |
| `page_path` | VARCHAR | Nullable |
| `properties_json` | VARCHAR | Not null |
| `product_id` | VARCHAR | Nullable |
| `order_id` | VARCHAR | Nullable |
| `value_cents` | BIGINT | Nullable |
| `currency` | VARCHAR | Nullable |
| `payment_method` | VARCHAR | Nullable |
| `delivery_method` | VARCHAR | Nullable |
| `delivery_courier` | VARCHAR | Nullable |
| `anonymized` | BOOLEAN | Not null, default `false` |

Index: unique `idx_analytics_event_id_session` on `(event_id, session_id)`.

`analytics_delivery_health`

| Column | Type | Nullability / notes |
|---|---:|---|
| `metric` | VARCHAR | Primary key |
| `value` | BIGINT | Not null |
| `updated_at` | TIMESTAMP | Not null |

Seeded metrics: `accepted`, `rejected`, `duplicate`, `validation_failure`.

`analytics_state`

| Column | Type | Nullability / notes |
|---|---:|---|
| `key` | VARCHAR | Primary key |
| `value` | VARCHAR | Not null |
| `updated_at` | TIMESTAMP | Not null |

## Courier Admin Schema Notes

Courier admin objects are active source schema, not local DB drift. Speedy and
Econt admin operations share the nullable courier metadata columns on `orders`
and the append-only `order_courier_events` audit table.

`order_courier_events`

| Column | Type | Constraints / notes |
|---|---:|---|
| `id` | INTEGER | Primary key autoincrement |
| `order_id` | TEXT | Not null, FK -> `orders(id)` `ON DELETE CASCADE` |
| `courier` | TEXT | Not null, one of `speedy`, `econt` |
| `action` | TEXT | Not null operation name |
| `status` | TEXT | Not null operation outcome |
| `request_json` | TEXT | Nullable redacted JSON request snapshot |
| `response_json` | TEXT | Nullable redacted JSON response snapshot |
| `error_json` | TEXT | Nullable redacted JSON error snapshot |
| `actor_user_id` | TEXT | Nullable admin actor id |
| `created_at` | TEXT | Not null, default `datetime('now')` |

Indexes:

- `idx_order_courier_events_order_created` on `(order_id, created_at)`.
- `idx_order_courier_events_courier_action` on `(courier, action, status)`.

Speedy admin writes events for health-adjacent actions where a local order is
involved: waybill creation/reuse, label print, tracking refresh, shipment search,
shipment info, cancellation, pickup terms, and pickup request. Stored request,
response, and error snapshots must be passed through the shared redaction helper
before insert.

Cancellation policy is intentionally conservative: Speedy cancellation success
marks shipment metadata as cancelled, but the customer order remains in its
existing lifecycle state. Speedy cancellation rejection records a failed event
without mutating the tracking number, courier status, or sync status.
