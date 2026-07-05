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
│   Sprint 2:  session-identity         Sprint 2:  frontend-event-sdk              │
│   Sprint 3:  google-oauth             Sprint 3:  ml-recommendations              │
│   Sprint 4:  cart-management          Sprint 4:  storefront-ui (data layer)      │
│   Sprint 5:  orders-checkout          Sprint 5:  storefront-ui (pages)           │
│   Sprint 6:  admin-dashboard          Sprint 6:  deployment-ci                   │
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
│   └── ml_compute.py
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

## Phase 2: Identity & SDK (Weeks 3–4)

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

## Phase 3: Auth & Intelligence (Weeks 5–6)

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

### Developer B: `ml-recommendations`

**What:** Feature engineering, candidate generation, ranking, caching, batch job

**Provides to others:**
- `GET /v1/recommendations` and `GET /v1/recommendations/trending`
- ML feature tables in DuckDB
- Background compute job (30min cycle)
- Recommendation response with "reason" field

**Depends on:**
- DuckDB events table from Phase 1 (own work) ✓
- Product catalog for filtering (Dev A Phase 1) ✓
- `.batch.lock` coordination (own work) ✓

**Key deliverables:**
```
app/models/recommendations.py
app/routes/recommendations.py
app/services/recommendation_service.py
app/jobs/ml_compute.py
tests/test_recommendations.py
```

---

### ★ Sync Point 2 (End of Week 6)

**What to validate:**
- [ ] OAuth login → session linking → identity resolution works end-to-end
- [ ] Recommendations serve correctly with cold-start fallback
- [ ] Session middleware doesn't break product/event routes
- [ ] Auth dependency (`get_current_user_optional`) wired into existing routes
- [ ] All background jobs coexist (batch loader + expiry + ML compute)
- [ ] Lock ordering is correct (no deadlocks under concurrent job runs)

---

## Phase 4: Commerce (Weeks 7–8)

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

### Developer B: `storefront-ui` (setup + data layer)

**What:** Next.js project init, API client, design system foundations, product pages

**Provides to others:**
- Frontend application shell
- API client with session header injection
- Design system tokens (colors, typography, spacing)

**Depends on:**
- Product API (Dev A Phase 1) ✓
- Event SDK (own Phase 2) ✓

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
- Recommendations API (own Phase 3) ✓

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
- [ ] Recommendations update based on user behavior
- [ ] Frontend ↔ backend session management works (rotation, expiry)
- [ ] Anonymous and authenticated checkout both work
- [ ] Order history accessible by session and by user

---

## Phase 6: Admin & Ops (Weeks 11–12)

### Developer A: `admin-dashboard`

**What:** Metrics aggregation, admin API, dashboard UI page

**Depends on:**
- Events in DuckDB (Dev B Phase 1) ✓
- Orders (own Phase 5) ✓
- Auth with is_admin (own Phase 3) ✓
- Products (own Phase 1) ✓

**Key deliverables:**
```
app/routes/admin.py
app/services/admin_service.py
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
deploy/atelier-api.service
deploy/atelier-ml.service
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
            ┌───────────────┼───────────────────────┼────────────────┐
            │               │                       │                │
            ▼               ▼                       ▼                ▼
   ┌────────────────┐  ┌─────────────┐  ┌──────────────────┐  ┌─────────┐
   │session-identity│  │cart-mgmt    │  │frontend-event-sdk│  │ml-recos │
   │   (Dev A)      │  │  (Dev A)    │  │    (Dev B)       │  │ (Dev B) │
   └───────┬────────┘  └──────┬──────┘  └──────────────────┘  └─────────┘
           │                   │                                     │
           ▼                   ▼                                     │
   ┌────────────────┐  ┌──────────────┐                             │
   │  google-oauth  │  │orders-checkout│                             │
   │   (Dev A)      │  │   (Dev A)    │                             │
   └───────┬────────┘  └──────┬───────┘                             │
           │                   │                                     │
           └─────────┬─────────┘─────────────────────────────────────┘
                     ▼
           ┌──────────────────┐          ┌──────────────────┐
           │ admin-dashboard  │          │  storefront-ui   │
           │    (Dev A)       │          │     (Dev B)      │
           └──────────────────┘          └──────────────────┘
                     │                            │
                     └────────────┬───────────────┘
                                  ▼
           ┌──────────────────┐          ┌──────────────────┐
           │maintenance-tooling│          │  deployment-ci   │
           │    (Dev A)        │          │     (Dev B)      │
           └──────────────────┘          └──────────────────┘
```

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
| 7 | `GET /v1/recommendations` | Dev B | Dev A (admin metrics) | Recommendation response |
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
| frontend-event-sdk | 47 | 2 | B | 2 |
| google-oauth | 65 | 2 | A | 3 |
| ml-recommendations | 70 | 2 | B | 3 |
| cart-management | 26 | 1.5 | A | 4 |
| storefront-ui (setup) | ~30 | 1.5 | B | 4 |
| orders-checkout | 39 | 2 | A | 5 |
| storefront-ui (features) | ~37 | 2 | B | 5 |
| admin-dashboard | 37 | 2 | A | 6 |
| deployment-ci | 73 | 2 | B | 6 |
| maintenance-tooling | 53 | 1 | A | 7 |
| Integration & polish | — | 1 | B | 7 |

**Total: ~13–14 weeks for two developers working in parallel.**

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
| 2 | Session middleware + cache | Browser SDK + consent | Sessions tracked, events emitted from browser |
| 3 | Google login + JWT + users | ML recs + batch job | Users can log in, get recommendations |
| 4 | Cart CRUD + stock validation | Frontend shell + product pages | Can add to cart, browse products in UI |
| 5 | Order creation + state machine | Cart drawer + checkout UI | Full purchase flow works |
| 6 | Admin dashboard + metrics | CI/CD + VPS deploy | Business metrics visible, auto-deploy works |
| 7 | Maintenance CLI + GDPR | E2E tests + hardening | Production-ready |