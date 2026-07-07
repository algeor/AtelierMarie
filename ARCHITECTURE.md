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
│         │  SQLite only                                                   │
│         ▼                                                                │
│  ┌─────────────────────┐                                                 │
│  │   SQLite (WAL)       │  ← System of Record                            │
│  │   atelier.db         │                                                 │
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

### SQLite Schema (System of Record)

```sql
-- Products: The core business entity
CREATE TABLE products (
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

-- Users: Optional (Google OAuth)
CREATE TABLE users (
    id          TEXT PRIMARY KEY,
    google_id   TEXT UNIQUE NOT NULL,
    email       TEXT UNIQUE NOT NULL,
    name        TEXT,
    avatar_url  TEXT,
    is_admin    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    last_login_at TEXT
);

-- Sessions: Cookie-based, for cart persistence
CREATE TABLE sessions (
    id          TEXT PRIMARY KEY,
    user_id     TEXT REFERENCES users(id),
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at  TEXT NOT NULL
);

-- Cart: Session-keyed
CREATE TABLE cart_items (
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    product_id  TEXT NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL DEFAULT 1,
    added_at    TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (session_id, product_id)
);

-- Orders
CREATE TABLE orders (
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

-- Order Items: Snapshot at purchase time
CREATE TABLE order_items (
    order_id    TEXT NOT NULL REFERENCES orders(id),
    product_id  TEXT NOT NULL,
    product_name TEXT NOT NULL,
    price_cents INTEGER NOT NULL,
    quantity    INTEGER NOT NULL,
    PRIMARY KEY (order_id, product_id)
);
```

### Data Flows (Synchronous)

**Browse products:**
```
Browser → GET /v1/products → SELECT FROM products WHERE is_active=1 → JSON response (~30ms)
```

**Add to cart:**
```
Browser → POST /v1/cart {product_id, quantity}
  → Validate stock (SELECT stock FROM products)
  → INSERT/UPDATE cart_items
  → Return updated cart (~50ms)
```

**Checkout:**
```
Browser → POST /v1/orders {email, address, ...}
  → BEGIN TRANSACTION
    → Validate all cart items still in stock
    → INSERT INTO orders
    → INSERT INTO order_items (snapshot prices)
    → UPDATE products SET stock = stock - quantity
    → DELETE FROM cart_items WHERE session_id = ?
  → COMMIT
  → Return order confirmation (~150ms)
  → AFTER RESPONSE: queue "purchase" event (fire-and-forget, Layer 2)
```

### Identity Model

```
Anonymous-first: Full functionality without login.

1. User visits → session cookie created (UUID v4)
2. User browses, carts, checks out → all keyed to session_id
3. User optionally logs in (Google OAuth) → session.user_id updated
4. Cart persists across the transition — it's session-keyed, already there
5. Orders show in "My Orders" if user_id matches

Login is an OVERLAY, not a prerequisite.
```

### API Surface (Layer 1)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/v1/products` | Public | List/search active products |
| GET | `/v1/products/{id}` | Public | Product detail |
| GET | `/v1/cart` | Session | Get cart contents with product info |
| POST | `/v1/cart` | Session | Add item to cart |
| PATCH | `/v1/cart/{product_id}` | Session | Update quantity |
| DELETE | `/v1/cart/{product_id}` | Session | Remove from cart |
| POST | `/v1/orders` | Session | Create order (checkout) |
| GET | `/v1/orders` | Session/JWT | List orders |
| GET | `/v1/orders/{id}` | Session/JWT | Order detail |
| GET | `/v1/auth/login` | Public | Google OAuth redirect |
| GET | `/v1/auth/callback` | Public | OAuth callback |
| GET | `/v1/auth/me` | JWT | Current user |
| POST | `/v1/auth/logout` | JWT/Session | Logout (clear JWT, rotate session) |
| POST | `/v1/admin/products` | Admin | Create product |
| PUT | `/v1/admin/products/{id}` | Admin | Update product |
| POST | `/v1/admin/products/import` | Admin | CSV bulk import |
| POST | `/v1/admin/products/{id}/image` | Admin | Upload product image |
| DELETE | `/v1/admin/products/{id}` | Admin | Deactivate product |
| GET | `/v1/admin/orders` | Admin | All orders (paginated) |
| PATCH | `/v1/admin/orders/{id}/status` | Admin | Update order status |

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
1. SQLite `sessions.user_id` is updated (Layer 1 — for cart/order association)
2. DuckDB `session_identity` gets a row (Layer 2 — for analytics attribution)

Old events are NEVER mutated. Analytics queries JOIN through `session_identity` to attribute anonymous behavior to users at read time.

---

## System Boundaries

### ✅ ALLOWED in Production Path (Layer 1)

- SQLite reads/writes
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

**Layer 1:** SQLite WAL mode handles concurrency natively. Multiple readers, single writer. 2 uvicorn workers can serve requests concurrently — reads are parallel, writes serialize naturally (and are fast, <5ms).

**Layer 2:** JSONL writes are append-only (`O_APPEND` — atomic for small writes, multi-worker safe). A single background thread reads JSONL files and loads into DuckDB. Only one writer to DuckDB at a time — no locks needed, it's just one thread.

**No file locks, no Kafka, no Redis.** JSONL + O_APPEND handles multi-worker writes. Single loader thread handles DuckDB.

---

## Deployment

```
Oracle Cloud Free Tier VPS (4 vCPU / 24GB RAM)
├── Nginx (reverse proxy + SSL + static files)
├── FastAPI (Uvicorn, 2 workers + background loader thread)
├── SQLite (atelier.db) — OLTP
├── DuckDB (analytics.db) — OLAP (optional, rebuildable from JSONL)
├── JSONL event files (data/events/) — crash-safe buffer
├── Next.js frontend (Node.js process, port 3000)
└── GitHub Actions (lint + test + deploy on push to main)
```

### Backup Strategy
- SQLite: daily `.backup` command → stored 7 days
- DuckDB: rebuildable from JSONL archives (no backup needed)
- JSONL archives: retained 30 days (gzipped)

---

## Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend | FastAPI + Uvicorn (Python 3.11) | Async-native, auto-docs, fast enough |
| Validation | Pydantic 2 | Type safety, serialization |
| OLTP DB | SQLite (WAL mode) | Embedded, zero-config, reliable, fast |
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
| 7 | **Zero-budget** | No paid services. SQLite + DuckDB + Oracle Free Tier |
| 8 | **Single developer** | Architecture sized for one person to build and maintain |
