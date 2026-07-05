# Atelier Marie — System Architecture

> Luxury candle e-commerce platform with event-driven analytics, ML recommendations, and zero-budget infrastructure.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              BROWSER / CLIENT                                    │
│                                                                                 │
│  ┌──────────────────────────────┐    ┌─────────────────────────────────────┐    │
│  │   Next.js 14 Storefront      │    │   Frontend Event SDK (~5KB)         │    │
│  │   App Router + RSC + Tailwind│    │   Vanilla JS, zero-dep             │    │
│  │                              │    │   Batch queue → sendBeacon fallback │    │
│  │  • Homepage / Hero           │    │   Consent-gated, localStorage      │    │
│  │  • Product Grid / PDP        │    │   session, client-gen event_id     │    │
│  │  • Cart Drawer (optimistic)  │    │                                     │    │
│  │  • Search Overlay            │    └───────────────┬─────────────────────┘    │
│  │  • Admin Dashboard           │                    │                           │
│  └──────────────┬───────────────┘                    │                           │
│                 │ fetch + X-Session-ID                │ POST /v1/events (batched) │
└─────────────────┼────────────────────────────────────┼───────────────────────────┘
                  │                                    │
══════════════════╪════════════════════════════════════╪═══════════════════════════════
                  │            NGINX + SSL             │
══════════════════╪════════════════════════════════════╪═══════════════════════════════
                  │                                    │
┌─────────────────▼────────────────────────────────────▼───────────────────────────┐
│                         FastAPI Application (Uvicorn × 2)                         │
│                                                                                   │
│  ┌─────────────┐ ┌─────────────┐ ┌──────────────┐ ┌───────────────────────────┐ │
│  │  Products   │ │    Cart     │ │   Orders     │ │   Auth (Google OAuth)     │ │
│  │  /v1/prods  │ │  /v1/cart   │ │  /v1/orders  │ │  /v1/auth/*              │ │
│  │             │ │             │ │              │ │  JWT HS256 + JWKS RS256   │ │
│  │  CRUD+Search│ │ Add/Remove  │ │ Checkout     │ │  Session linking          │ │
│  │  CSV Import │ │ Stock check │ │ State machine│ │  First-user-is-admin      │ │
│  └──────┬──────┘ └──────┬──────┘ └──────┬───────┘ └────────────┬────────────┘ │
│         │                │               │                      │               │
│  ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼───────┐             │               │
│  │  Sessions   │ │   Events    │ │    Admin     │◄────────────┘               │
│  │  /v1/sess   │ │  /v1/events │ │  /v1/admin   │                             │
│  │             │ │             │ │              │                             │
│  │ In-memory   │ │ 202 Accept  │ │ Metrics      │                             │
│  │ cache+flush │ │ JSONL write │ │ Event log    │                             │
│  │ Header-based│ │ <10ms       │ │ Product perf │                             │
│  └──────┬──────┘ └──────┬──────┘ └──────┬───────┘                             │
│         │                │               │                                     │
│  ┌──────▼────────────────▼───────────────▼───────────────────────────────────┐ │
│  │                       SERVICE LAYER                                        │ │
│  │   • Stock validation    • Event emission (fire-and-forget)                 │ │
│  │   • Order lifecycle     • Identity resolution (read-time JOINs)            │ │
│  │   • Recommendation engine (fallback chain)                                 │ │
│  └───────┬──────────────────────────────────────────┬────────────────────────┘ │
│          │                                          │                           │
└──────────┼──────────────────────────────────────────┼───────────────────────────┘
           │                                          │
┌──────────▼──────────────────┐    ┌──────────────────▼─────────────────────────────┐
│     SQLite (atelier.db)     │    │              JSONL Buffer Layer                 │
│     WAL Mode — OLTP         │    │                                                 │
│                             │    │   events_2024-01-15.jsonl  ← O_APPEND atomic    │
│  ┌─────────┐ ┌───────────┐ │    │   events_2024-01-16.jsonl                       │
│  │products │ │ cart_items │ │    │                                                 │
│  ├─────────┤ ├───────────┤ │    │   .batch.lock  (fcntl.flock)                    │
│  │ orders  │ │order_items│ │    └────────────────────┬────────────────────────────┘
│  ├─────────┤ └───────────┘ │                         │ Batch loader (60s interval)
│  │  users  │               │                         │ INSERT OR IGNORE (dedup)
│  └─────────┘               │                         ▼
└─────────────────────────────┘    ┌────────────────────────────────────────────────┐
                                   │          DuckDB (analytics.db)                   │
                                   │          Single-writer — OLAP                   │
                                   │                                                 │
                                   │   ┌──────────┐  ┌─────────────────┐             │
                                   │   │  events  │  │session_identity │             │
                                   │   └─────┬────┘  └────────┬────────┘             │
                                   │         │                 │                      │
                                   │   ┌─────▼─────────────────▼─────┐               │
                                   │   │   ML Feature Tables          │               │
                                   │   │   (rebuilt every 30min)      │               │
                                   │   │   • item_popularity          │               │
                                   │   │   • co_occurrence            │               │
                                   │   │   • session_sequences        │               │
                                   │   │   • click_through_rates      │               │
                                   │   └─────────────────────────────┘               │
                                   └────────────────────────────────────────────────┘
```

## Dual-Database Architecture

The single most important architectural decision: **SQLite for transactions, DuckDB for analytics.**

| Concern | SQLite (atelier.db) | DuckDB (analytics.db) |
|---------|--------------------|-----------------------|
| **Role** | OLTP — source of truth for entities | OLAP — analytical read layer |
| **Data** | Products, users, orders, cart | Events, sessions, ML features |
| **Access** | WAL mode (unlimited readers + 1 writer) | Single-writer, file-lock guarded |
| **Latency** | <5ms reads/writes | Batch-optimized (60s ingestion cycles) |
| **Backup** | `.backup` command (consistent) | File copy during lock acquisition |

## Data Flow: Event Lifecycle

```
 Browser Click              API (< 10ms)           JSONL Buffer            DuckDB (60s)
 ───────────── ──────────── ──────────── ──────────── ──────────── ──────────────────

 page_view ──────┐
 add_to_cart ────┤  SDK batches   POST /v1/events    append to         Batch loader
 purchase ──────┤  (10 events    ────────────────▶   events_DATE.jsonl ────────────▶  INSERT OR IGNORE
 search ────────┘   or 5s)        202 Accepted       (O_APPEND safe)      (dedup via event_id)

                                  Server stamps:                      Archives processed
                                  - received_at                       files after load
                                  - validates schema
```

## Identity Model

```
                         Anonymous-First Architecture
                         ═══════════════════════════

  ┌───────────┐                    ┌──────────────┐
  │  Browser  │ ── X-Session-ID ──▶│  Session     │
  │ (SDK gen  │    (every request) │  Middleware   │
  │  UUID v4) │                    └──────┬───────┘
  └───────────┘                           │
                                          ▼
                             ┌─────────────────────────┐
                             │   In-Memory Session Cache │
                             │   {session_id → state}   │
                             │   30min idle / 24h hard   │
                             └────────────┬────────────┘
                                          │
           ┌──────────────────────────────┼──────────────────────────┐
           │                              │                          │
           ▼                              ▼                          ▼
  ┌─────────────────┐        ┌──────────────────────┐    ┌──────────────────┐
  │ Anonymous User   │        │   Google OAuth Login  │    │  Session Expiry   │
  │ (session only)   │        │   POST /v1/auth/login │    │  Background job   │
  │                  │        │                       │    │  (5 min interval) │
  │ Can: browse,     │        │  On success:          │    │                   │
  │ cart, checkout   │        │  link(session, user)  │    │  Synthesizes      │
  │                  │        │  ▼                    │    │  session_end      │
  └──────────────────┘        │  Retroactive          │    │  events           │
                              │  attribution via      │    └──────────────────┘
                              │  read-time JOINs      │
                              └──────────────────────┘
```

**Key insight:** Events are never backfilled. Identity resolution happens at query time via JOINs on `session_identity` — events remain immutable.

## ML Recommendations Pipeline

```
  ┌─────────────────────────────────────────────────────────────┐
  │              Batch Job (every 30 min)                        │
  │              .ml-compute.lock acquired                       │
  │                                                             │
  │   DuckDB ──▶ Feature Engineering (pure SQL) ──▶ Feature     │
  │              • item_popularity                   Tables      │
  │              • co_occurrence_matrix                          │
  │              • session_sequences                             │
  │              • click_through_rates                           │
  └───────────────────────────────────────────────┬─────────────┘
                                                  │
                                                  ▼
  ┌─────────────────────────────────────────────────────────────┐
  │              API Request: GET /v1/recommendations            │
  │                                                             │
  │   ┌─────────────┐    ┌─────────────┐    ┌──────────────┐   │
  │   │  Candidate  │───▶│   Ranking   │───▶│  Filtering   │   │
  │   │ Generation  │    │  (weighted  │    │  (remove     │   │
  │   │ (50-100     │    │   linear)   │    │   seen,      │   │
  │   │  items)     │    │             │    │   inactive)  │   │
  │   └─────────────┘    └─────────────┘    └──────────────┘   │
  │                                                             │
  │   Fallback Chain:                                           │
  │   Personalized (≥20 events) → Session (≥3) → Popular → Featured │
  │                                                             │
  │   Cache: In-memory dict, TTL 5-30min, LRU @ 10K entries     │
  └─────────────────────────────────────────────────────────────┘
```

## Concurrency & Coordination

The zero-budget constraint means no Redis, no message queue — coordination is file-lock based:

```
  ┌──────────────────────────────────────────────────────────────┐
  │                    Lock Hierarchy                              │
  │                                                               │
  │   .batch.lock ─────────── Guards DuckDB writes                │
  │   ├── Event Batch Loader (every 60s)                          │
  │   ├── Session Flush (every 5 min)                             │
  │   └── Backup Script (daily 3am)                               │
  │                                                               │
  │   .ml-compute.lock ────── Guards ML feature rebuild            │
  │   └── ML Batch Job (every 30 min)                             │
  │                                                               │
  │   .maintenance.lock ───── Guards destructive ops               │
  │   └── Maintenance CLI (cleanup, rebuild, GDPR)                │
  │                                                               │
  │   Ordering: maintenance acquires BOTH .batch + .ml-compute    │
  │             before proceeding (prevents deadlocks)             │
  └──────────────────────────────────────────────────────────────┘
```

## Deployment Topology

```
  ┌─────────────────────────────────────────────────────────────────┐
  │  Oracle Cloud Free Tier VPS (4 vCPU / 24GB RAM / 200GB disk)    │
  │                                                                 │
  │  ┌────────────────┐        ┌────────────────────────────┐       │
  │  │   Nginx        │        │   Systemd Services          │       │
  │  │   :80 → :443   │───────▶│                             │       │
  │  │   Let's Encrypt │        │   atelier-api.service       │       │
  │  │   rate limiting │        │   └── uvicorn × 2 workers   │       │
  │  └────────────────┘        │                             │       │
  │                            │   atelier-ml.service         │       │
  │  ┌────────────────┐        │   └── ML batch (30min loop)  │       │
  │  │   Cron Jobs    │        │                             │       │
  │  │   3am: cleanup │        └────────────────────────────┘       │
  │  │   weekly: vacuum│                                            │
  │  │   hourly: disk  │        ┌────────────────────────────┐       │
  │  │     monitor     │        │   Data                     │       │
  │  └────────────────┘        │   /opt/atelier/             │       │
  │                            │   ├── atelier.db (SQLite)   │       │
  │                            │   ├── analytics.db (DuckDB) │       │
  │                            │   ├── events/*.jsonl        │       │
  │                            │   └── backups/ (7-day)      │       │
  │                            └────────────────────────────┘       │
  └─────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────┐
  │  GitHub Actions (Free Tier)           │
  │                                       │
  │  Push to main:                        │
  │  ┌──────┐  ┌──────┐  ┌──────────┐    │
  │  │ Lint │─▶│ Test │─▶│ Deploy   │    │
  │  │(ruff)│  │(pytest)│  │(SSH pull)│    │
  │  └──────┘  └──────┘  └──────────┘    │
  └──────────────────────────────────────┘
```

## Implementation Order

```
  Phase 1 (Foundations)           Phase 2 (Core Commerce)        Phase 3 (Intelligence)
  ═══════════════════            ═══════════════════════         ═══════════════════════

  ┌──────────────────┐           ┌──────────────────┐           ┌──────────────────┐
  │ product-catalog  │◄──────────│  cart-management │           │ml-recommendations│
  └──────────────────┘           └──────────────────┘           └──────────────────┘
                                         │                              ▲
  ┌──────────────────┐                   ▼                              │
  │ session-identity │◄──────────┌──────────────────┐           ┌──────┴───────────┐
  └──────────────────┘           │ orders-checkout  │           │ admin-dashboard  │
         ▲                       └──────────────────┘           └──────────────────┘
         │                                                              ▲
  ┌──────┴───────────┐                                                  │
  │   google-oauth   │──────────────────────────────────────────────────┘
  └──────────────────┘

  ┌──────────────────┐           ┌──────────────────┐           ┌──────────────────┐
  │event-ingestion   │           │frontend-event-sdk│           │ storefront-ui    │
  │    pipeline      │◄──────────│                  │───────────│                  │
  └──────────────────┘           └──────────────────┘           └──────────────────┘

  Phase 4 (Operations)
  ═══════════════════
  ┌──────────────────┐           ┌──────────────────┐
  │  deployment-ci   │           │maintenance-tooling│
  └──────────────────┘           └──────────────────┘
```

**Critical path:** `product-catalog` → `session-identity` → `event-ingestion-pipeline` → everything else.

## Architectural Principles

| # | Principle | Rationale |
|---|-----------|-----------|
| 1 | **Zero-budget** | No Redis, no Kafka, no paid APIs. SQLite + DuckDB + file locks + in-memory caches |
| 2 | **Anonymous-first** | Full functionality without login. Identity is optional overlay |
| 3 | **Fire-and-forget events** | Business transactions never blocked by analytics pipeline |
| 4 | **Read-time resolution** | Identity linking via JOINs, not event mutation |
| 5 | **Batch over stream** | JSONL buffer → DuckDB every 60s. ML features every 30min. Metrics cached 5min |
| 6 | **Soft deletes everywhere** | Products deactivated not deleted. GDPR = nullify, not cascade |
| 7 | **Service layer abstraction** | Route handlers thin, business logic testable independently |
| 8 | **Graceful degradation** | Every system has a fallback chain (recommendations, sessions, events) |
| 9 | **API-first** | JSON responses, header-based sessions, no server-side rendering dependencies |
| 10 | **Single-writer protection** | File locks serialize DuckDB access across API, batch, ML, and maintenance |

## Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | Next.js 14, React Server Components, Tailwind CSS | SEO, performance, luxury aesthetic control |
| Event SDK | Vanilla JS, sendBeacon | Zero dependencies, <5KB |
| API | FastAPI + Uvicorn | Async-native, great DX, auto-docs |
| Auth | Google OAuth 2.0, JWT HS256, httpx | No third-party auth libs, minimal deps |
| OLTP DB | SQLite WAL | Free, embedded, reliable, zero-config |
| OLAP DB | DuckDB | Columnar analytics, embedded, SQL-native |
| Buffer | JSONL files (O_APPEND) | Crash-safe, zero-latency writes |
| ML | Pure SQL features + weighted linear ranker | No pandas/numpy, auditable, fast |
| Reverse Proxy | Nginx + Let's Encrypt | SSL termination, rate limiting |
| Process Mgmt | systemd | Auto-restart, logging, socket activation |
| CI/CD | GitHub Actions → SSH deploy | Free tier, sub-60s deploys |
| Hosting | Oracle Cloud Free Tier | 4 vCPU, 24GB RAM, $0/month |

## Data Models

### SQLite (atelier.db)

```sql
-- Product Catalog
CREATE TABLE products (
    id          TEXT PRIMARY KEY,   -- business identifier / SKU
    name        TEXT NOT NULL,
    description TEXT,
    price       REAL NOT NULL,
    category    TEXT,
    image_url   TEXT,
    stock       INTEGER DEFAULT 0,
    is_active   INTEGER DEFAULT 1,  -- soft delete
    is_featured INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

-- Users (Google OAuth)
CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    google_id     TEXT UNIQUE NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    name          TEXT,
    avatar_url    TEXT,
    is_admin      INTEGER DEFAULT 0,
    created_at    TEXT DEFAULT (datetime('now')),
    last_login_at TEXT
);

-- Cart (session-keyed)
CREATE TABLE cart_items (
    session_id TEXT NOT NULL,
    product_id TEXT NOT NULL REFERENCES products(id),
    quantity   INTEGER NOT NULL DEFAULT 1,
    added_at   TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (session_id, product_id)
);

-- Orders
CREATE TABLE orders (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id     TEXT NOT NULL,
    user_id        INTEGER REFERENCES users(id),
    total          REAL NOT NULL,
    status         TEXT NOT NULL DEFAULT 'pending',
    payment_method TEXT NOT NULL DEFAULT 'cod',
    created_at     TEXT DEFAULT (datetime('now')),
    updated_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE order_items (
    order_id          INTEGER NOT NULL REFERENCES orders(id),
    product_id        TEXT NOT NULL REFERENCES products(id),
    quantity          INTEGER NOT NULL,
    price_at_purchase REAL NOT NULL,
    PRIMARY KEY (order_id, product_id)
);
```

### DuckDB (analytics.db)

```sql
-- Events (append-only)
CREATE TABLE events (
    event_id    VARCHAR PRIMARY KEY,  -- client-generated UUID
    session_id  VARCHAR NOT NULL,
    user_id     VARCHAR,
    event_type  VARCHAR NOT NULL,
    payload     JSON,
    timestamp   TIMESTAMP NOT NULL,
    received_at TIMESTAMP NOT NULL
);

-- Session Identity (batch-flushed from memory)
CREATE TABLE session_identity (
    session_id VARCHAR PRIMARY KEY,
    user_id    VARCHAR,
    first_seen TIMESTAMP NOT NULL,
    last_seen  TIMESTAMP NOT NULL,
    is_expired BOOLEAN DEFAULT FALSE
);

-- ML Feature Tables (rebuilt every 30min)
CREATE TABLE item_popularity AS ...;
CREATE TABLE co_occurrence AS ...;
CREATE TABLE session_sequences AS ...;
CREATE TABLE click_through_rates AS ...;
```

## API Surface

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/v1/products` | Public | List/search products |
| GET | `/v1/products/{id}` | Public | Product detail |
| POST | `/v1/products` | API Key | Create product |
| PUT | `/v1/products/{id}` | API Key | Update product |
| DELETE | `/v1/products/{id}` | API Key | Deactivate product |
| POST | `/v1/products/import` | API Key | CSV bulk import |
| GET | `/v1/cart` | Session | Get cart contents |
| POST | `/v1/cart` | Session | Add item |
| PATCH | `/v1/cart/{product_id}` | Session | Update quantity |
| DELETE | `/v1/cart/{product_id}` | Session | Remove item |
| POST | `/v1/cart/checkout` | Session | Checkout cart |
| GET | `/v1/orders` | Session/JWT | List orders |
| GET | `/v1/orders/{id}` | Session/JWT | Order detail |
| POST | `/v1/orders/{id}/cancel` | Session/JWT | Cancel order |
| POST | `/v1/events` | Session | Ingest event batch |
| GET | `/v1/auth/login` | Public | Get OAuth redirect URL |
| GET | `/v1/auth/callback` | Public | OAuth callback |
| GET | `/v1/auth/me` | JWT | Current user profile |
| POST | `/v1/auth/logout` | JWT | Logout + rotate session |
| GET | `/v1/recommendations` | Session | Get recommendations |
| GET | `/v1/admin/metrics` | Admin | Dashboard metrics |
| GET | `/v1/admin/events` | Admin | Paginated event log |
| GET | `/v1/admin/products` | Admin | Product performance |
| GET | `/v1/admin/orders` | Admin | Order management |

## Risks & Open Questions

| Risk | Impact | Mitigation |
|------|--------|------------|
| DuckDB single-writer bottleneck | Analytics freshness delayed if lock contention | Lock timeout + retry; batch jobs stagger schedules |
| In-memory session cache lost on restart | All active sessions invalidated | Acceptable for MVP; could persist to SQLite later |
| SQLite write contention under load | Cart/order writes queue behind each other | WAL mode + fast transactions (<5ms); unlikely to matter at expected scale |
| No real-time updates | Admin dashboard stale for up to 5 minutes | Acceptable for single-operator; add SSE later if needed |
| No payment gateway | COD-only limits conversion | Extensible status enum; payment integration is a future change |
| Oracle Free Tier reliability | VPS may be reclaimed or throttled | Daily backups; git-based deploy allows quick re-provision |