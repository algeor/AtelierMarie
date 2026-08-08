# System Design — AtelierMarie

High-level architecture, layers, and data flows.

## Core Principle

**Build a reliable e-commerce system first. Analytics/ML are optional detachable layers.**

The system is split into two strict layers:
- **Layer 1 (Production):** Sells candles. Must be fast, reliable, works perfectly with Layer 2 completely OFF.
- **Layer 2 (Sandbox):** Collects events, runs analytics, experiments with ML. Async-only, non-blocking, allowed to fail silently.

---

## System Overview

```
┌─────────────────────────────────────────────┐
│         Browser (Next.js Frontend)          │
│  Product pages, cart, checkout, account     │
└──────────────────┬──────────────────────────┘
                   │ API calls (JSON)
                   ▼
        ┌──────────────────────┐
        │  Nginx (reverse proxy│
        │  SSL, rate limiting) │
        └──────────┬───────────┘
                   ▼
    ┌──────────────────────────────┐
    │  FastAPI (Uvicorn, 2 workers)│
    │  ├─ Layer 1: E-commerce      │
    │  │  └─ Products, Cart,       │
    │  │     Orders, Payments      │
    │  └─ Layer 2: Analytics       │
    │     └─ Events, DuckDB        │
    └──────────┬───────────────────┘
               │
        ┌──────┴───────┐
        ▼              ▼
    ┌────────┐    ┌──────────┐
    │Postgres│    │ DuckDB   │
    │(OLTP)  │    │(OLAP)    │
    │Layer 1 │    │Layer 2   │
    └────────┘    └──────────┘
```

---

## Layer 1: Production E-Commerce

**SLA:** All operations <200ms. Zero dependency on Layer 2.

### Core Entities

- **Products:** Catalog with bilingual names, pricing (cents), stock, taxonomy
- **Sessions:** Cookie-based identity (UUID), optional user link
- **Cart:** Session-keyed items, quantity validation
- **Orders:** Immutable purchase records with item snapshots
- **Payments:** Stripe checkout sessions + pay-on-delivery
- **Delivery:** Econt/Speedy courier integration, live pricing
- **Users:** Optional Google OAuth accounts

### Key Design Decisions

| Decision | Why |
|----------|-----|
| **Postgres** | Multi-worker concurrency (MVCC), full-text search, strong ACID |
| **Prices as integer cents** | No floating-point errors (EUR 35.00 = 3500 cents) |
| **Product IDs are text slugs** | Immutable; order items snapshot product name+price at purchase time |
| **Order items are immutable** | Historical accuracy: if product price changes, old orders unchanged |
| **Session-first identity** | Anonymous checkout works; users can log in later without losing cart |
| **Stock validation at add** | Return 409 immediately if out of stock (don't wait until checkout) |

### Data Flows

**Browse products:**
```
GET /v1/products?search=lavender
  → FTS search (GIN index on name+description)
  → Filter by category/stock/active
  → Return paginated results (~30ms)
```

**Add to cart:**
```
POST /v1/cart {product_id, quantity}
  → Validate stock available ≥ quantity
  → If not → 409 Conflict {available: N}
  → INSERT/UPDATE cart_items
  → Return full cart (~50ms)
```

**Checkout (COD/Bank Transfer):**
```
POST /v1/orders {email, delivery_courier, payment_method}
  → BEGIN TRANSACTION
  → Validate cart not empty
  → Validate all items in stock
  → Get live courier quote (Econt/Speedy)
  → INSERT orders + order_items (snapshot prices)
  → UPDATE products SET stock = stock - quantity
  → DELETE cart_items WHERE session_id = ?
  → COMMIT
  → Return order confirmation (~150-200ms)
  → AFTER RESPONSE: queue email (outbox), fire analytics event
```

**Card payment checkout (Stripe):**
```
POST /v1/orders/stripe
  → CREATE order, set reserved_until = now + 15min
  → CREATE Stripe Checkout Session
  → Return session_id + client_secret to frontend
  → (user completes payment on Stripe.com)
  → Stripe webhook: payment.succeeded
  → UPDATE order.payment_status = 'paid'
  → Expiry cleanup job: every 1min, restore stock for expired unpaid orders
```

---

## Layer 2: Analytics & ML Sandbox

**Non-critical, async-only, fails silently.**

### Event Collection

Events appended to JSONL (crash-safe), then loaded into DuckDB every 60 seconds:

```
User action → HTTP response sent → append to JSONL (O_APPEND, atomic)
                                       ↓
                          Background thread (every 60s)
                                       ↓
                                    DuckDB
```

Why JSONL?
- Crash-safe: events on disk survive process restart
- Multi-worker safe: multiple uvicorn workers can append concurrently
- Rebuildable: if DuckDB corrupts, replay all JSONL files

### Event Types

| Event | Triggered By | Payload |
|-------|-------------|---------|
| `page_view` | Product page loaded | `{product_id}` |
| `add_to_cart` | Item added to cart | `{product_id, quantity}` |
| `purchase` | Order completed | `{order_id, total_cents}` |

---

## System Boundaries

### ✅ ALLOWED in Layer 1

- Postgres reads/writes
- Session cookie operations
- Google OAuth (login only)
- Operations completing in <200ms

### ❌ FORBIDDEN in Layer 1

- Any DuckDB query or write
- Any import from `app/analytics/` or `app/ml/`
- Any background job dependency
- Any operation whose failure prevents checkout

### ⚡ ASYNC ONLY (Layer 2)

- Event ingestion
- DuckDB writes
- ML computation
- Analytics queries (admin dashboard only)

---

## API Surface (60+ Endpoints)

| Category | Count | Examples |
|----------|-------|----------|
| Products | 7 | List, search, detail, admin CRUD, upload |
| Cart | 6 | Get, add, update, remove, quote |
| Checkout & Orders | 5 | Create order, list, detail, tracking |
| Authentication | 4 | Google OAuth, get user, logout |
| Social | 2 | Reactions, comments |
| Admin | 18+ | Dashboard, orders, taxonomy, content, analytics |
| System | 3 | Health check, consent, events |

Full reference: `api/ENDPOINTS.md`

---

## Concurrency Model

**Layer 1 (Postgres):** MVCC handles multiple readers/writers. Connection pool with timeouts.

**Layer 2 (DuckDB):** Single background thread writes. No locks needed—it's just one writer.

**No Redis, no Kafka, no file locks.** JSONL + O_APPEND handles multi-worker writes. Single loader thread handles DuckDB.

---

## Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Backend | FastAPI + Uvicorn | Async-native, auto-docs, fast |
| Frontend | Next.js 15 | App Router, SSR, SEO, luxury UI |
| OLTP DB | Postgres | MVCC, concurrency, FTS, ACID |
| OLAP DB | DuckDB (optional) | Columnar analytics, embedded |
| Auth | Google OAuth 2.0 + JWT | No password management |
| Payments | Stripe | No PCI compliance burden |
| Shipping | Econt + Speedy | Live pricing, office/door delivery |
| Email | Jinja2 + ZeptoMail | Durable outbox, plain-text templates |
| I18n | next-intl | Bilingual (en/bg), locale routing |

---

## Deployment

```
Oracle Cloud Free Tier (4 vCPU, 24GB RAM)
├── Nginx (reverse proxy, SSL, rate limiting)
├── FastAPI (Uvicorn, 2 workers, reload disabled in prod)
├── Postgres (atelier_marie) — OLTP
├── DuckDB (analytics.db) — OLAP, optional
├── JSONL event files — crash-safe buffer
├── Next.js frontend — static + SSR
└── systemd services — auto-restart
```

---

## Architectural Principles

| # | Principle | Rationale |
|---|-----------|-----------|
| 1 | **E-commerce first** | Store must work perfectly without analytics/ML |
| 2 | **Layer separation** | Layer 1 code never imports Layer 2 modules |
| 3 | **Anonymous-first** | Full functionality without login |
| 4 | **Simple over clever** | No JSONL buffers, file locks, or tiered refresh |
| 5 | **Async analytics** | Events are fire-and-forget; ML pre-computed |
| 6 | **Graceful degradation** | Recommendations: ML → popularity → random (never error) |
| 7 | **Zero-budget** | No paid services. Postgres + DuckDB + Oracle Free Tier |

---

## See Also

- **Database schema:** `database/SCHEMA.md`
- **API reference:** `api/ENDPOINTS.md`
- **Design decisions:** `architecture/DECISIONS.md`
