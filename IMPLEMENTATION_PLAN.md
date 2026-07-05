# Atelier Marie — Implementation Plan

> Parallel development guide for two developers with minimal friction.

## TL;DR — Who Works on What

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        PARALLEL DEVELOPMENT MAP                                   │
│                                                                                   │
│   Developer A (Backend Core)          Developer B (Data & Analytics)              │
│   ════════════════════════            ═══════════════════════════════             │
│                                                                                   │
│   Sprint 1:  product-catalog          Sprint 1:  event-ingestion-pipeline         │
│   Sprint 2:  session-identity         Sprint 2:  analytics-layer ★ NEW            │
│   Sprint 3:  google-oauth             Sprint 3:  frontend-event-sdk              │
│   Sprint 4:  cart-management          Sprint 4:  ml-recommendations (lighter)    │
│   Sprint 5:  orders-checkout          Sprint 5:  storefront-ui (data + pages)    │
│   Sprint 6:  admin-dashboard (lighter)Sprint 6:  deployment-ci                   │
│   Sprint 7:  maintenance-tooling      Sprint 7:  (integration testing)           │
│                                                                                   │
│   Sync Points: ★ after Sprint 1, ★ after Sprint 3, ★ after Sprint 5             │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 0: Contracts First (Day 1 — both devs together)

Before splitting, agree on these shared interfaces. This prevents integration pain later.

### Shared Contracts to Define Upfront

| Contract | File | What to Agree |
|----------|------|---------------|
| Event schema | `app/models/events.py` | EventType enum, event payload shape |
| Product response | `app/models/products.py` | Public product fields, pagination format |
| Session header | `app/middleware/session.py` | `X-Session-ID` format (UUID v4), response headers |
| Config shape | `app/config.py` | All env vars, pydantic-settings model |
| DB init | `app/database.py` | SQLite + DuckDB connection factories |
| File lock paths | `app/constants.py` | `.batch.lock`, `.ml-compute.lock`, `.maintenance.lock` |
| Project structure | See below | Agreed package layout |

### Agreed Project Structure

```
app/
├── __init__.py
├── main.py                    # FastAPI app factory + lifespan
├── config.py                  # pydantic-settings (all env vars)
├── constants.py               # Lock paths, timeouts, limits
├── database.py                # SQLite + DuckDB connection management
├── middleware/
│   └── session.py             # X-Session-ID middleware
├── analytics/                 # Shared analytics layer ★ NEW
│   ├── __init__.py
│   ├── compute.py             # Orchestrator (tier1 + conditional tier2)
│   ├── scheduler.py           # 5-min background loop
│   └── queries/               # SQL-as-files (auditable, testable)
│       ├── product_metrics.sql
│       ├── session_metrics.sql
│       ├── search_terms.sql
│       ├── funnel.sql
│       ├── popularity.sql
│       ├── cooccurrence.sql
│       ├── session_sequences.sql
│       └── ctr.sql
├── models/                    # Pydantic schemas (shared contracts)
│   ├── events.py
│   ├── products.py
│   ├── cart.py
│   ├── orders.py
│   ├── users.py
│   └── recommendations.py
├── routes/                    # FastAPI routers (thin)
│   ├── products.py
│   ├── cart.py
│   ├── orders.py
│   ├── events.py
│   ├── auth.py
│   ├── recommendations.py
│   └── admin.py
├── services/                  # Business logic (testable)
│   ├── product_service.py
│   ├── cart_service.py
│   ├── order_service.py
│   ├── event_service.py
│   ├── session_service.py
│   ├── auth_service.py
│   ├── recommendation_service.py
│   └── admin_service.py
├── jobs/                      # Background tasks
│   ├── batch_loader.py
│   ├── session_expiry.py
│   └── ml_precompute.py       # Reads analytics tables, warms rec cache
├── maintenance/               # CLI module
│   ├── __main__.py
│   ├── cleanup.py
│   ├── gdpr.py
│   ├── rebuild.py
│   └── diagnostics.py
└── data/                      # Runtime data (gitignored)
    ├── atelier.db
    ├── analytics.db
    ├── events/
    │   └── events_YYYY-MM-DD.jsonl
    └── backups/

frontend/                      # Next.js app (separate package)
├── app/
├── components/
├── lib/
└── ...

sdk/                           # Frontend event SDK
├── src/
│   └── tracker.js
├── dist/
└── package.json
```

---

## Phase 1: Foundations (Weeks 1–2)

### Developer A: `product-catalog`

**What:** SQLite schema, product CRUD, CSV import, public read API

**Provides to others:**
- `products` table in `atelier.db`
- `GET /v1/products` and `GET /v1/products/{id}` (public)
- Admin routes behind API key
- `product_service.get_product()`, `product_service.check_stock()`

**No dependencies** — can start immediately.

**Key deliverables:**
```
app/database.py          (SQLite connection + WAL init)
app/config.py            (pydantic-settings skeleton)
app/models/products.py   (request/response schemas)
app/routes/products.py   (CRUD + search endpoints)
app/services/product_service.py
tests/test_products.py
```

---

### Developer B: `event-ingestion-pipeline`

**What:** JSONL buffer writer, DuckDB schema, batch loader, `POST /v1/events`

**Provides to others:**
- `events` table in `analytics.db`
- `POST /v1/events` endpoint (202 Accepted)
- JSONL writer (reusable for fire-and-forget emission)
- Batch loader background job
- `.batch.lock` coordination pattern

**No dependencies** — can start immediately.

**Key deliverables:**
```
app/database.py          (DuckDB connection — coordinate with Dev A)
app/models/events.py     (EventType enum, EventCreate schema)
app/routes/events.py     (POST /v1/events)
app/services/event_service.py (JSONL writer)
app/jobs/batch_loader.py
tests/test_events.py
```

---

### ★ Sync Point 1 (End of Week 2)

**What to validate:**
- [ ] Both devs can run `pytest` with both SQLite and DuckDB initialized
- [ ] `app/database.py` handles both databases cleanly
- [ ] `app/config.py` has all env vars for both services
- [ ] Event schema (EventType enum) is finalized
- [ ] Product response schema is finalized
- [ ] File lock pattern is tested and documented

---

## Phase 2: Identity & Analytics Layer (Weeks 3–4)

### Developer A: `session-identity`

**What:** In-memory session cache, middleware, session linking, expiry job

**Provides to others:**
- `X-Session-ID` middleware (all subsequent routes get session context)
- `session_identity` table in DuckDB
- Background expiry job
- `session_service.get_session()`, `session_service.link_user()`

**Depends on:**
- DuckDB connection from Phase 1 (Dev B's work) ✓

**Key deliverables:**
```
app/middleware/session.py
app/services/session_service.py
app/jobs/session_expiry.py
tests/test_sessions.py
```

---

### Developer B: `analytics-layer` ★ NEW

**What:** Shared analytics compute job, SQL-as-files, tiered refresh, materialized tables

**Provides to others:**
- 8 `analytics_*` DuckDB tables consumed by ML recs + admin dashboard + storefront
- Tier 1 refresh (5-min): product_metrics, session_metrics, search_terms, funnel
- Tier 2 refresh (30-min): popularity, cooccurrence, session_sequences, ctr
- Health endpoint fields for analytics freshness
- CLI trigger for on-demand rebuild

**Depends on:**
- DuckDB events table from Phase 1 (own work) ✓
- Session identity table (Dev A Phase 2 — partial: analytics can run with empty session_identity)

**Key deliverables:**
```
app/analytics/__init__.py
app/analytics/compute.py       (orchestrator: tier1 + conditional tier2)
app/analytics/scheduler.py     (5-min background loop)
app/analytics/queries/product_metrics.sql
app/analytics/queries/session_metrics.sql
app/analytics/queries/search_terms.sql
app/analytics/queries/funnel.sql
app/analytics/queries/popularity.sql
app/analytics/queries/cooccurrence.sql
app/analytics/queries/session_sequences.sql
app/analytics/queries/ctr.sql
tests/test_analytics.py
```

---

### ★ Sync Point 1 (End of Week 4)

**What to validate:**
- [ ] Both devs can run `pytest` with both SQLite and DuckDB initialized
- [ ] `app/database.py` handles both databases cleanly
- [ ] `app/config.py` has all env vars for both services
- [ ] Event schema (EventType enum) is finalized
- [ ] Product response schema is finalized
- [ ] `.batch.lock` works correctly with event loader + session expiry + analytics compute
- [ ] Analytics tables exist and are populated from test events
- [ ] Health endpoint shows analytics freshness

---

## Phase 3: Auth & SDK (Weeks 5–6)

### Developer A: `google-oauth`

**What:** OAuth flow, JWT, users table, session linking

**Provides to others:**
- `users` table in SQLite
- `GET /v1/auth/login`, `GET /v1/auth/callback`, `GET /v1/auth/me`
- `get_current_user()` dependency for protected routes
- `is_admin` flag for admin access

**Depends on:**
- Session middleware from Phase 2 (own work) ✓
- `POST /v1/sessions/link` from session-identity ✓

**Key deliverables:**
```
app/models/users.py
app/routes/auth.py
app/services/auth_service.py
tests/test_auth.py
```

---

### Developer B: `frontend-event-sdk`

**What:** Browser SDK, batch queue, sendBeacon, consent gate

**Provides to others:**
- `@atelier/tracker` JavaScript module
- Handles session rotation from server headers
- Consent-gated tracking

**Depends on:**
- `POST /v1/events` endpoint from Phase 1 (own work) ✓

**Key deliverables:**
```
sdk/src/tracker.js
sdk/src/queue.js
sdk/src/transport.js
sdk/package.json           (esbuild config)
sdk/tests/tracker.test.js
```

---

### ★ Sync Point 2 (End of Week 6)

**What to validate:**
- [ ] OAuth login → session linking → identity resolution works end-to-end
- [ ] Session middleware doesn't break product/event routes
- [ ] Auth dependency (`get_current_user_optional`) wired into existing routes
- [ ] Frontend SDK emits events correctly and handles session rotation
- [ ] All background jobs coexist (batch loader + expiry + analytics compute)
- [ ] Lock coordination works (no deadlocks under concurrent job runs)

---

## Phase 4: Commerce & ML (Weeks 7–8)

### Developer A: `cart-management`

**What:** Cart state, add/remove, stock validation, checkout trigger

**Provides to others:**
- Cart API (GET, POST, PATCH, DELETE, checkout)
- Cart events emitted to pipeline
- Checkout delegates to order creation

**Depends on:**
- Product catalog (own Phase 1) ✓
- Session middleware (own Phase 2) ✓
- Event emission (Dev B Phase 1) ✓

**Key deliverables:**
```
app/models/cart.py
app/routes/cart.py
app/services/cart_service.py
tests/test_cart.py
```

---

### Developer B: `ml-recommendations` (lighter — no feature computation)

**What:** Candidate generation, ranking, filtering, caching, precomputation batch job

**Note:** Feature computation is handled by the analytics layer (Phase 2). The ML service only **reads** from `analytics_*` tables — no DuckDB writes, no file locks needed.

**Provides to others:**
- `GET /v1/recommendations` and `GET /v1/recommendations/trending`
- Background precomputation job (30min cycle, reads analytics tables, warms cache)
- Recommendation response with "reason" field
- Fallback chain (personalized → session → popularity → featured)

**Depends on:**
- Analytics layer (own Phase 2) ✓
- Product catalog for filtering (Dev A Phase 1) ✓

**Key deliverables:**
```
app/models/recommendations.py
app/routes/recommendations.py
app/services/recommendation_service.py
app/jobs/ml_precompute.py         (reads analytics tables, no lock needed)
tests/test_recommendations.py
```

---

### Developer B also starts: `storefront-ui` (setup + data layer)

**What:** Next.js project init, API client, design system foundations, product pages

**Key deliverables:**
```
frontend/package.json
frontend/app/layout.tsx
frontend/lib/api.ts        (fetch wrapper + X-Session-ID)
frontend/lib/theme.ts      (design tokens)
frontend/app/(shop)/page.tsx          (homepage)
frontend/app/(shop)/products/page.tsx (product grid)
frontend/app/(shop)/products/[id]/page.tsx (PDP)
```

---

## Phase 5: Checkout & UI (Weeks 9–10)

### Developer A: `orders-checkout`

**What:** Order creation, state machine, order history, purchase events

**Provides to others:**
- Order API (create, list, get, status transitions)
- Purchase event emission
- Price snapshot at purchase time

**Depends on:**
- Cart checkout (own Phase 4) ✓
- Product pricing (own Phase 1) ✓
- Auth for user-linked orders (own Phase 3) ✓

**Key deliverables:**
```
app/models/orders.py
app/routes/orders.py
app/services/order_service.py
tests/test_orders.py
```

---

### Developer B: `storefront-ui` (interactive features)

**What:** Cart drawer, search overlay, auth flow, navigation, footer

**Depends on:**
- Cart API (Dev A Phase 4) ✓
- Auth endpoints (Dev A Phase 3) ✓
- Recommendations API (own Phase 4) ✓

**Key deliverables:**
```
frontend/components/CartDrawer.tsx
frontend/components/SearchOverlay.tsx
frontend/components/Navigation.tsx
frontend/components/Footer.tsx
frontend/app/(shop)/checkout/page.tsx
frontend/contexts/CartContext.tsx
```

---

### ★ Sync Point 3 (End of Week 10)

**What to validate:**
- [ ] Full purchase flow: browse → add to cart → checkout → order confirmation
- [ ] Event tracking fires correctly at each step
- [ ] Recommendations update based on user behavior (via analytics layer refresh)
- [ ] Frontend ↔ backend session management works (rotation, expiry)
- [ ] Anonymous and authenticated checkout both work
- [ ] Order history accessible by session and by user

---

## Phase 6: Admin & Ops (Weeks 11–12)

### Developer A: `admin-dashboard` (lighter — reads analytics tables)

**What:** Admin API endpoints, dashboard UI page. Metrics come from pre-materialized `analytics_*` tables — no complex aggregation logic needed.

**Depends on:**
- Analytics layer tables (Dev B Phase 2) ✓
- Orders (own Phase 5) ✓
- Auth with is_admin (own Phase 3) ✓
- Products (own Phase 1) ✓

**Key deliverables:**
```
app/routes/admin.py
app/services/admin_service.py     (thin — reads from analytics_* tables)
frontend/app/(admin)/dashboard/page.tsx
tests/test_admin.py
```

---

### Developer B: `deployment-ci`

**What:** GitHub Actions, server provisioning, systemd, nginx, backups

**Depends on:**
- All services running correctly ✓

**Key deliverables:**
```
.github/workflows/ci.yml
deploy/setup.sh
deploy/deploy.sh
deploy/backup.sh
deploy/atelier-api.service    (single service: API + all background jobs)
deploy/nginx.conf
```

---

## Phase 7: Hardening (Week 13)

### Developer A: `maintenance-tooling`

**What:** CLI for cleanup, GDPR, rebuild, diagnostics

**Key deliverables:**
```
app/maintenance/__main__.py
app/maintenance/cleanup.py
app/maintenance/gdpr.py
app/maintenance/rebuild.py
app/maintenance/diagnostics.py
tests/test_maintenance.py
```

### Developer B: Integration testing & polish

**What:** End-to-end tests, performance profiling, documentation

---

## Dependency Graph (What Blocks What)

```
                    NOTHING BLOCKS THESE (start day 1)
                    ─────────────────────────────────
                    ┌────────────────┐   ┌──────────────────────┐
                    │product-catalog │   │event-ingestion-pipeline│
                    │   (Dev A)      │   │      (Dev B)           │
                    └───────┬────────┘   └──────────┬─────────────┘
                            │                       │
            ┌───────────────┤                       │
            │               │                       ▼
            │               │            ┌──────────────────────┐
            │               │            │  ★ analytics-layer ★  │
            │               │            │      (Dev B)          │
            │               │            └──────────┬────────────┘
            │               │                       │
            ▼               ▼                       ├──────────────────────┐
   ┌────────────────┐  ┌─────────────┐             ▼                      ▼
   │session-identity│  │cart-mgmt    │  ┌──────────────────┐  ┌──────────────────┐
   │   (Dev A)      │  │  (Dev A)    │  │  ml-recos        │  │ admin-dashboard  │
   └───────┬────────┘  └──────┬──────┘  │  (Dev B, lighter)│  │ (Dev A, lighter) │
           │                   │         └──────────────────┘  └──────────────────┘
           ▼                   ▼
   ┌────────────────┐  ┌──────────────┐
   │  google-oauth  │  │orders-checkout│
   │   (Dev A)      │  │   (Dev A)    │
   └───────┬────────┘  └──────────────┘
           │
           ▼
   ┌──────────────────┐          ┌──────────────────┐
   │frontend-event-sdk│          │  storefront-ui   │
   │    (Dev B)       │          │     (Dev B)      │
   └──────────────────┘          └──────────────────┘
                                          │
                                          ▼
           ┌──────────────────┐          ┌──────────────────┐
           │maintenance-tooling│          │  deployment-ci   │
           │    (Dev A)        │          │     (Dev B)      │
           └──────────────────┘          └──────────────────┘
```

**Key change:** The analytics layer sits between event-ingestion-pipeline and its consumers (ML recs, admin dashboard). Both consumers are now **lighter** because they read pre-materialized tables instead of computing their own aggregates.

## Interface Boundaries (Minimal Coupling Points)

These are the **only** points where Dev A and Dev B's code touches. Everything else is independent:

| # | Interface | Owner | Consumer | Contract |
|---|-----------|-------|----------|----------|
| 1 | `app/database.py` | Both (co-author Day 1) | Everything | SQLite + DuckDB factory |
| 2 | `app/config.py` | Both (co-author Day 1) | Everything | Env var definitions |
| 3 | `app/models/events.py` | Dev B | Dev A (cart/order emit) | EventType enum, payload shapes |
| 4 | `app/middleware/session.py` | Dev A | Dev B (SDK reads headers) | X-Session-ID, X-Session-Expired |
| 5 | `POST /v1/events` | Dev B | Dev A (fire-and-forget calls) | Request/response schemas |
| 6 | `GET /v1/products` | Dev A | Dev B (frontend, ML) | Product response schema |
| 7 | `analytics_*` tables | Dev B | Dev A (admin dashboard) | Table schemas agreed in analytics-layer spec |
| 8 | `.batch.lock` protocol | Dev B | Dev A (session flush) | fcntl.flock, non-blocking try |

### Rules to Avoid Merge Conflicts

1. **Own your directory:** Dev A owns `routes/products.py`, `routes/cart.py`, `routes/orders.py`, `routes/auth.py`, `routes/admin.py`. Dev B owns `routes/events.py`, `routes/recommendations.py`.
2. **Shared files use append-only patterns:** `app/main.py` includes routers — each dev adds their own router import. No rewriting the same lines.
3. **Models are contracts:** Once a model schema is merged, changes require a sync conversation.
4. **Tests are independent:** Each dev's tests live in their own test files. No shared test fixtures beyond `conftest.py` (co-authored).
5. **Feature branches:** Each change gets its own branch. Merge to main only at sync points after both devs validate integration.

---

## Effort Estimates

| Change | Tasks | Weeks | Developer | Sprint |
|--------|-------|-------|-----------|--------|
| product-catalog | 67 | 2 | A | 1 |
| event-ingestion-pipeline | 65 | 2 | B | 1 |
| session-identity | 72 | 2 | A | 2 |
| analytics-layer ★ | ~25 | 1.5 | B | 2 |
| google-oauth | 65 | 2 | A | 3 |
| frontend-event-sdk | 47 | 2 | B | 3 |
| cart-management | 26 | 1.5 | A | 4 |
| ml-recommendations | ~40 | 1.5 | B | 4 |
| orders-checkout | 39 | 2 | A | 5 |
| storefront-ui | 67 | 3 | B | 4–5 |
| admin-dashboard | ~25 | 1.5 | A | 6 |
| deployment-ci | 73 | 2 | B | 6 |
| maintenance-tooling | 53 | 1 | A | 7 |
| Integration & polish | — | 1 | B | 7 |

**Total: ~13 weeks for two developers working in parallel.**

Note: `ml-recommendations` and `admin-dashboard` are lighter than originally estimated because the analytics layer handles all aggregate computation. ML drops from ~70 to ~40 tasks (no feature engineering). Admin drops from ~37 to ~25 tasks (no query logic, just read from tables).

---

## Risk Mitigation

| Risk | How We Avoid It |
|------|-----------------|
| Merge conflicts in `main.py` | Each dev adds router in separate line; use `include_router()` pattern |
| Schema drift between frontend/backend | Models defined once in `app/models/`; frontend types generated from OpenAPI |
| DuckDB lock starvation | Non-blocking `flock()` with exponential backoff; jobs stagger by offset |
| Session middleware breaks existing tests | Dev A adds middleware with path-based opt-in; existing tests unaffected |
| Frontend blocked on backend APIs | Dev B can mock APIs locally; contract schemas agreed upfront |
| OAuth hard to test locally | Dev A provides `ATELIER_AUTH_BYPASS=true` for dev mode (skips Google) |

---

## Quick Reference: What Each Sprint Delivers

| Sprint | Dev A Ships | Dev B Ships | End State |
|--------|-------------|-------------|-----------|
| 1 | Products API + SQLite | Events API + DuckDB + JSONL | Can browse products, ingest events |
| 2 | Session middleware + cache | Analytics layer (8 tables, tiered refresh) | Sessions tracked, analytics materialized |
| 3 | Google login + JWT + users | Browser SDK + consent | Users can log in, events emitted from browser |
| 4 | Cart CRUD + stock validation | ML recs (reads analytics tables) + frontend shell | Can add to cart, get recommendations, browse UI |
| 5 | Order creation + state machine | Cart drawer + checkout UI | Full purchase flow works |
| 6 | Admin dashboard (reads analytics tables) | CI/CD + VPS deploy | Business metrics visible, auto-deploy works |
| 7 | Maintenance CLI + GDPR | E2E tests + hardening | Production-ready |