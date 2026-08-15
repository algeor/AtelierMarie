# Atelier Marie — System Architecture

> Luxury candle e-commerce platform. Optional analytics & ML sandbox for learning.

## Core Principle

**Build a reliable e-commerce system first. ML is a detachable intelligence layer, not part of the core product.**

The system is split into two strict layers:
- **Layer 1 (Production):** Sells candles. Must be fast, reliable, and work perfectly with Layer 2 completely OFF.
- **Layer 2 (Sandbox):** Collects events, runs analytics, experiments with ML. Async-only, non-blocking, allowed to fail silently.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           BROWSER                                        │
│                                                                         │
│   ┌──────────────────────────┐          ┌─────────────────────────┐     │
│   │   Next.js Storefront     │          │  Event tracking          │     │
│   │   (separate app)         │          │  (simple fetch calls)    │     │
│   │                          │          │                          │     │
│   │  • Product pages         │          │  Fires AFTER page loads  │     │
│   │  • Cart                  │          │  Never blocks UI         │     │
│   │  • Checkout              │          │  Can fail silently       │     │
│   │  • Account               │          │                          │     │
│   └──────────┬───────────────┘          └──────────┬──────────────┘     │
│              │ API calls (JSON)                     │ POST /v1/events    │
└──────────────┼─────────────────────────────────────┼────────────────────┘
               │                                     │
═══════════════╪═════════════════════════════════════╪═════════════════════
               │              NGINX + SSL             │
═══════════════╪═════════════════════════════════════╪═════════════════════
               │                                     │
┌──────────────▼─────────────────────────────────────▼────────────────────┐
│                    FastAPI Application (Uvicorn)                          │
│                                                                          │
│  ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐   │
│  │ LAYER 1 — PRODUCTION (synchronous, <200ms)                     │   │
│  │                                                                 │   │
│  │  GET /v1/products          GET /v1/cart                         │   │
│  │  GET /v1/products/{id}     POST /v1/cart                        │   │
│  │  POST /v1/admin/products   PATCH /v1/cart/{product_id}          │   │
│  │  PUT /v1/admin/products    DELETE /v1/cart/{product_id}         │   │
│  │                                                                 │   │
│  │  POST /v1/orders           GET /v1/auth/login                   │   │
│  │  GET /v1/orders            GET /v1/auth/callback                │   │
│  │  GET /v1/orders/{id}       GET /v1/auth/me                      │   │
│  │                            POST /v1/auth/logout                 │   │
│  │                                                                 │   │
│  │  GET /v1/admin/orders      GET /v1/admin/dashboard              │   │
│  │                            POST /v1/admin/products/{id}/image   │   │
│  │                                                                 │   │
│  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘   │
│         │                                                                │
│         │  Postgres only                                                 │
│         ▼                                                                │
│  ┌─────────────────────┐                                                 │
│  │   Postgres           │  ← System of Record                            │
│  │   atelier_marie      │                                                 │
│  │                      │                                                 │
│  │   products           │                                                 │
│  │   users              │                                                 │
│  │   sessions           │                                                 │
│  │   cart_items          │                                                 │
│  │   orders             │                                                 │
│  │   order_items        │                                                 │
│  └─────────────────────┘                                                 │
│                                                                          │
│  ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐   │
│  │ LAYER 2 — SANDBOX (async, non-blocking, can fail)              │   │
│  │                                                                 │   │
│  │  POST /v1/events (202 Accepted, fire-and-forget)                │   │
│  │  GET /v1/recommendations (best-effort, fallback to popular)     │   │
│  │  GET /v1/admin/analytics (reads DuckDB, admin-only)             │   │
│  │                                                                 │   │
│  │  Background thread: flush event queue → DuckDB                  │   │
│  │  Background job (30min): compute recommendations → cache        │   │
│  │                                                                 │   │
│  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘   │
│         │                                                                │
│         ▼                                                                │
│  ┌─────────────────────┐      ┌────────────────────────────┐            │
│  │   DuckDB             │      │  Recommendation Cache       │            │
│  │   analytics.db       │      │  (SQLite table or JSON)     │            │
│  │                      │      │                             │            │
│  │   events             │      │  Pre-computed by bg job     │            │
│  │   session_identity   │      │  Read synchronously         │            │
│  └─────────────────────┘      └────────────────────────────┘            │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Production E-Commerce

### Design Requirements

| Requirement | Target |
|-------------|--------|
| Product page load | <50ms |
| Add to cart | <50ms |
| Checkout (create order) | <200ms |
| Zero dependency on Layer 2 | Must work if DuckDB is deleted |
| Zero dependency on external services | Except Google OAuth (optional) |

### Data Model Overview

**Core entities:**
- **Products:** Catalog items with localized names/descriptions (en/bg), pricing in cents, stock levels, taxonomy (types/categories/labels)
- **Users:** Optional Google OAuth accounts with admin flag
- **Sessions:** Cookie-based anonymous identity, links to user on login
- **Cart:** Session-keyed shopping cart with quantity limits (1-10 per item, 20 distinct max)
- **Orders:** Immutable purchase records with items snapshots (prices frozen at purchase time)
- **Delivery & Shipping:** Econt/Speedy courier integration with live pricing, office/door delivery methods
- **Payments:** Stripe checkout sessions + pay-on-delivery support, separate payment_status from order fulfillment status
- **Content:** Managed FAQ sections/items, Atelier/about pages, site banners, taxonomy

**Key design:** All prices as integer cents. Product IDs are business slugs (e.g., `lavender-dream-300ml`). Order items are immutable snapshots—never joined back to products table.

### Postgres Schema (System of Record)

**Full schema reference:** `docs/DATABASE_SCHEMA.md` contains detailed table definitions, foreign keys, indexes, and constraints.

**Key tables:**
```
products (id, name_en/bg, description_en/bg, price_cents, stock, category_slug, type_slug)
│
├─ product_images (id, product_id, image_url, thumbnail_url, zoom_url, is_primary)
├─ product_videos (id, product_id, status, video_url, poster_url, duration_secs)
├─ product_label_assignments (product_id, label_slug)
│
users (id, google_id, email, is_admin, last_login_at)
│
sessions (id, user_id, preferred_locale, expires_at)
│
├─ cart_items (session_id, product_id, quantity)
├─ analytics_consents (session_id, analytics, consent_version)
│
orders (id, session_id, user_id, status, payment_status, payment_method, ...)
│
├─ order_items (order_id, product_id, product_name, price_cents, quantity)
├─ order_emails (order_id, event, recipient, status)
├─ order_courier_events (order_id, courier, action, status, request/response json)
```

### Data Flows (Synchronous)

**Browse & search products:**
```
GET /v1/products?search=lavender&category=classic&page=1&limit=20
  → FTS search on name_en/description_en (GIN indexes) + category/stock filters
  → Paginated {items, total, page, limit} response (~30ms)
```

**Add to cart:**
```
POST /v1/cart {product_id, quantity}
  → Validate stock available ≥ quantity
  → If not → 409 Conflict {available: N}
  → INSERT/UPDATE cart_items
  → Return full cart with product details (~50ms)
```

**Checkout:**
```
POST /v1/orders {email, delivery_method, delivery_courier, payment_method, ...}
  → BEGIN TRANSACTION
    → Validate cart not empty
    → Validate all items still in stock
    → Get live courier quote (Econt/Speedy) if applicable
    → INSERT INTO orders
    → INSERT INTO order_items (snapshot: product_name, price_cents, quantity)
    → UPDATE products SET stock = stock - quantity
    → DELETE FROM cart_items WHERE session_id = ?
  → COMMIT
  → Return order {id, order_number, total_cents, status='pending'} (~150-200ms)
  → AFTER RESPONSE: fire "purchase" event (Layer 2), queue transactional email (outbox)
```

**Card payment checkout (Stripe):**
```
POST /v1/orders/stripe {email, ...}
  → CREATE order with payment_method='card', payment_status='pending'
  → CREATE Stripe Checkout Session
  → Set reserved_until = now + 15 minutes
  → Return {session_id, client_secret} to frontend
  → After webhook: update payment_status → 'paid' or 'failed'
  → Expired card orders: cleanup job restores stock every 1 min
```

### Identity Model

```
Anonymous-first: Full functionality without login.

1. User visits → session cookie created (UUID v4)
2. User browses, carts, checks out → all keyed to session_id
3. Optional login (Google OAuth) → session.user_id updated, JWT issued
4. Cart persists across login transition — it's session-keyed, already there
5. Orders show in "My Orders" if user_id matches
6. Session expires after 30 days; cleanup runs hourly

Login is an OVERLAY, not a prerequisite.
```

### Complete API Reference

For exhaustive endpoint definitions, see `docs/API.md`.

**Products & Catalog:**
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/v1/products` | Public | List/search active products with pagination |
| GET | `/v1/products/{id}` | Public | Product detail with reactions/comments counts |
| POST | `/v1/admin/products` | Admin | Create product |
| PUT | `/v1/admin/products/{id}` | Admin | Update product |
| DELETE | `/v1/admin/products/{id}` | Admin | Deactivate product (soft delete) |
| POST | `/v1/admin/products/import` | Admin | CSV bulk import (streaming, upsert per row) |
| POST | `/v1/admin/products/{id}/image` | Admin | Upload product image (creates thumbnail + zoom) |
| DELETE | `/v1/admin/products/{id}/image/{image_id}` | Admin | Delete product image |
| POST | `/v1/admin/products/{id}/video` | Admin | Upload product video (queues transcode) |
| GET | `/v1/admin/products/{id}/video/status` | Admin | Video transcode status |

**Cart & Checkout:**
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/v1/cart` | Session | Get cart contents with product details |
| POST | `/v1/cart` | Session | Add item to cart (validates stock) |
| PATCH | `/v1/cart/{product_id}` | Session | Update quantity or remove (qty=0) |
| DELETE | `/v1/cart/{product_id}` | Session | Remove item from cart |
| GET | `/v1/delivery/quote` | Public | Get live courier quotes (Speedy/Econt) |
| POST | `/v1/orders` | Session | Create order (checkout with COD/bank transfer) |
| POST | `/v1/orders/stripe` | Session | Create Stripe checkout session + order |
| GET | `/v1/orders` | Session/JWT | List user's orders (paginated) |
| GET | `/v1/orders/{id}` | Session/JWT | Order detail with timeline + tracking |

**Auth:**
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/v1/auth/login` | Public | Google OAuth redirect + PKCE flow |
| GET | `/v1/auth/callback` | Public | OAuth callback, create/link user, issue JWT |
| GET | `/v1/auth/me` | JWT/Session | Current user + admin flag |
| POST | `/v1/auth/logout` | JWT/Session | Logout (invalidate JWT, rotate session ID) |

**Social & Content:**
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/v1/products/{id}/reactions` | Session | Toggle emoji reaction (heart, thumbs_up) |
| GET | `/v1/products/{id}/reactions` | Public | Reaction counts by type |
| POST | `/v1/products/{id}/comments` | Session | Post comment (sanitized, display_name) |
| GET | `/v1/products/{id}/comments` | Public | List comments for product |
| DELETE | `/v1/products/{id}/comments/{comment_id}` | Admin | Hide/delete comment |
| POST | `/v1/contact` | Public | Submit contact form (rate-limited, queues email) |
| GET | `/v1/faq` | Public | List FAQ sections + items by locale |
| GET | `/v1/about` | Public | Get about/atelier page sections |

**Admin & Settings:**
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/v1/admin/dashboard` | Admin | Stats (orders, revenue, top products) |
| GET | `/v1/admin/orders` | Admin | All orders (paginated, filterable by status/payment) |
| PATCH | `/v1/admin/orders/{id}/status` | Admin | Update fulfillment status (pending → confirmed → shipped → delivered) |
| PATCH | `/v1/admin/orders/{id}/payment-status` | Admin | Update payment status (manual override for COD) |
| GET | `/v1/admin/orders/{id}/courier` | Admin | Courier tracking + shipment details |
| POST | `/v1/admin/orders/{id}/courier/create-waybill` | Admin | Create Speedy/Econt shipment |
| GET | `/v1/admin/taxonomy` | Admin | Product types, categories, labels |
| POST | `/v1/admin/taxonomy/{entity}` | Admin | Create type/category/label |
| PUT | `/v1/admin/taxonomy/{entity}/{slug}` | Admin | Update taxonomy entry |
| GET | `/v1/admin/delivery` | Admin | Delivery settings (courier methods enabled) |
| PUT | `/v1/admin/delivery` | Admin | Update delivery settings |
| GET | `/v1/admin/delivery/speedy` | Admin | Speedy admin operations + health check |
| GET | `/v1/admin/delivery/econt` | Admin | Econt admin operations + health check |
| GET | `/v1/admin/faq` | Admin | List FAQ sections + items (draft/published) |
| POST | `/v1/admin/faq/sections` | Admin | Create FAQ section |
| POST | `/v1/admin/faq/items` | Admin | Create FAQ item |
| PUT | `/v1/admin/faq/items/{id}` | Admin | Update FAQ item |
| GET | `/v1/admin/about` | Admin | List about page sections |
| POST | `/v1/admin/about/sections` | Admin | Create about section |
| PUT | `/v1/admin/about/sections/{slug}` | Admin | Update about section |
| GET | `/v1/settings/payments` | Public | Payment method availability (card/COD/bank transfer) |
| GET | `/v1/admin/analytics` | Admin | Funnel analytics dashboard + CSV export |

**System & Health:**
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | Public | Health check (DB, DuckDB, background jobs status) |
| POST | `/v1/analytics/consent` | Session | Record cookie consent (opt-in for tracking) |
| POST | `/v1/analytics/events` | Session | Submit analytics event (fire-and-forget, Layer 2) |

---

## Layer 2: Analytics & ML Sandbox

### Design Requirements

| Requirement | How |
|-------------|-----|
| Never blocks user-facing requests | All writes async (background thread) |
| Can crash without affecting checkout | Wrapped in try/except, failures logged not raised |
| Can be completely disabled | Feature flag `ANALYTICS_ENABLED=false` |
| Data is rebuildable | Events are the source; analytics are derived |

### Event Collection

Events are appended to daily JSONL files (crash-safe, multi-worker safe via `O_APPEND`), then loaded into DuckDB by a background thread every 60 seconds.

```
User action completes → HTTP response sent → append to JSONL (O_APPEND, atomic)
                                                    │
                                          Background thread (every 60s)
                                                    │  reads JSONL → INSERT OR IGNORE
                                                    ▼
                                              DuckDB (analytics.db)
```

**Why JSONL (not in-memory queue):**
- Crash-safe: if the process dies, events on disk survive
- Multi-worker safe: 2 uvicorn workers can both append to the same file (O_APPEND)
- Debuggable: `cat events_2026-07-05.jsonl | wc -l`
- Rebuildable: if DuckDB corrupts, replay all JSONL files to reconstruct it

Still simple — one file append per event, one background thread for loading. No Kafka, no Redis.

### DuckDB Schema (Analytics Only)

```sql
-- Raw events: append-only log
CREATE TABLE events (
    event_id    VARCHAR PRIMARY KEY,
    event_type  VARCHAR NOT NULL,
    session_id  VARCHAR NOT NULL,
    user_id     VARCHAR,
    product_id  VARCHAR,
    payload     JSON,
    timestamp   TIMESTAMP NOT NULL,
    received_at TIMESTAMP DEFAULT now()
);

-- Session identity: links anonymous sessions to users (on login)
CREATE TABLE session_identity (
    session_id  VARCHAR NOT NULL,
    user_id     VARCHAR NOT NULL,
    linked_at   TIMESTAMP DEFAULT now(),
    PRIMARY KEY (session_id, user_id)
);
```

### Event Types

| Event | Triggered By | Payload |
|-------|-------------|---------|
| `page_view` | Product page loaded | `{product_id}` |
| `add_to_cart` | Item added to cart | `{product_id, quantity}` |
| `remove_from_cart` | Item removed | `{product_id}` |
| `purchase` | Order completed | `{order_id, total_cents, item_count}` |
| `search` | Search performed | `{query, result_count}` |

### ML Recommendations (Experimental)

A background job runs every 30 minutes:
1. Reads events from DuckDB (co-occurrence, popularity)
2. Computes simple recommendation scores
3. Writes results to a `recommendations` table (SQLite or JSON cache)

Product pages read from this cache **synchronously**:
- If cache has recommendations → show them
- If cache is empty/stale → show "Popular products" (sorted by order count from SQLite)
- If that fails too → show random 4 active products

**The recommendation system is a learning exercise. It must NEVER be on the critical path.**

### Identity Resolution (Analytics-Only)

When a user logs in via Google OAuth:
1. Postgres `sessions.user_id` is updated (Layer 1 — for cart/order association)
2. DuckDB `session_identity` gets a row (Layer 2 — for analytics attribution)

Old events are NEVER mutated. Analytics queries JOIN through `session_identity` to attribute anonymous behavior to users at read time.

---

## System Boundaries

### ✅ ALLOWED in Production Path (Layer 1)

- Postgres reads/writes
- Session cookie operations
- Google OAuth external call (login only)
- Any operation completing in <200ms

### ❌ FORBIDDEN in Production Path (Layer 1)

- Any DuckDB query or write
- Any operation from `app/analytics/` or `app/ml/`
- Any background job dependency
- Any operation whose failure would prevent browsing or checkout
- Any `import` from Layer 2 modules in Layer 1 route handlers

### ⚡ ASYNC ONLY (Layer 2)

- Event ingestion (queued after response sent)
- DuckDB writes (background thread)
- ML computation (scheduled job)
- Analytics queries (admin dashboard only, never user-facing)

---

## Concurrency Model

**Layer 1:** Postgres MVCC plus a psycopg connection pool handle concurrency. Multiple readers and writers run concurrently — readers never block writers. 2 uvicorn workers can serve requests concurrently, and writes are fast (<5ms).

**Layer 2:** JSONL writes are append-only (`O_APPEND` — atomic for small writes, multi-worker safe). A single background thread reads JSONL files and loads into DuckDB. Only one writer to DuckDB at a time — no locks needed, it's just one thread.

**No file locks, no Kafka, no Redis.** JSONL + O_APPEND handles multi-worker writes. Single loader thread handles DuckDB.

---

## Deployment

```
Oracle Cloud Free Tier VPS (4 vCPU / 24GB RAM)
├── Nginx (reverse proxy + SSL + static files)
├── FastAPI (Uvicorn, 2 workers + background loader thread)
├── Postgres (atelier_marie) — OLTP
├── DuckDB (analytics.db) — OLAP (optional, rebuildable from JSONL)
├── JSONL event files (data/events/) — crash-safe buffer
├── Next.js frontend (Node.js process, port 3000)
└── GitHub Actions (lint + test + deploy on push to main)
```

### Backup Strategy
- Postgres: daily `pg_dump` → stored 7 days
- DuckDB: rebuildable from JSONL archives (no backup needed)
- JSONL archives: retained 30 days (gzipped)

---

## Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend | FastAPI + Uvicorn (Python 3.11) | Async-native, auto-docs, fast enough |
| Validation | Pydantic 2 | Type safety, serialization |
| OLTP DB | Postgres | Reliable, concurrent, MVCC, strong SQL |
| Auth | Google OAuth 2.0 + JWT (PyJWT) | No password management needed |
| Frontend | Next.js 14 (separate app) | Rich UI, SEO, luxury aesthetic |
| OLAP DB | DuckDB (Layer 2 only) | Columnar analytics, embedded |
| Scheduling | APScheduler (in-process) | Background jobs without external deps |
| Reverse Proxy | Nginx + Let's Encrypt | SSL, rate limiting, static serving |
| Hosting | Oracle Cloud Free Tier | $0/month, 4 vCPU, 24GB RAM |
| CI/CD | GitHub Actions | Free, lint + test + deploy |

---

## Architectural Principles

| # | Principle | Rationale |
|---|-----------|-----------|
| 1 | **E-commerce first** | The store must work perfectly without analytics or ML |
| 2 | **Layer separation** | Layer 1 code never imports Layer 2 modules |
| 3 | **Anonymous-first** | Full functionality without login |
| 4 | **Simple over clever** | No JSONL buffers, no file locks, no tiered refresh — not needed at this scale |
| 5 | **Async analytics** | Events are fire-and-forget; ML is pre-computed; never on the critical path |
| 6 | **Graceful degradation** | Recommendations: ML → popularity → random. Never an error. |
| 7 | **Zero-budget** | No paid services. Postgres + DuckDB + Oracle Free Tier |
| 8 | **Single developer** | Architecture sized for one person to build and maintain |
