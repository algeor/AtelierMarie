# Atelier Marie — Implementation Plan

> Single developer, 3 phases. Ship the store first, add analytics later, experiment with ML when ready.

## Philosophy

**Phase 1 is the product. Phases 2 and 3 are learning exercises.**

Your mom's shop needs to sell candles. That's Phase 1. Everything after that is for your personal ML/data engineering education — valuable, but never at the cost of the store working.

---

## Phase 1: Ship the Store (Weeks 1–2)

**Goal:** The store is LIVE and selling candles online.

After Phase 1, the website is fully functional: customers can browse products, add to cart, checkout, and your mom can manage products and orders via an admin panel.

### Week 1: Backend + Admin

| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | Project setup | `pyproject.toml`, venv, FastAPI scaffold, SQLite schema, `app/` structure |
| 2 | Product catalog | `GET /v1/products`, `GET /v1/products/{id}`, admin CRUD |
| 3 | Session + Cart | Session cookie middleware, add/remove/update cart items |
| 4 | Checkout + Orders | Create order (atomic transaction), order history, admin order management |
| 5 | Auth | Google OAuth login, JWT sessions, first-user-is-admin, protected admin routes |

### Week 2: Frontend + Deploy

| Day | Task | Deliverable |
|-----|------|-------------|
| 6–7 | Next.js storefront | Product listing, product detail page, cart, checkout flow |
| 8 | Admin pages | Product management UI, order list with status updates |
| 9 | Polish | Mobile responsive, error handling, loading states, basic SEO |
| 10 | Deploy | Oracle Cloud VPS, Nginx + SSL, systemd, GitHub Actions CI/CD |

### Phase 1 Deliverables

```
app/
├── __init__.py
├── main.py              # FastAPI app factory + lifespan
├── config.py            # pydantic-settings (env vars)
├── database.py          # SQLite connection (WAL mode)
├── middleware/
│   └── session.py       # Session cookie middleware
├── models/              # Pydantic schemas
│   ├── products.py
│   ├── cart.py
│   ├── orders.py
│   └── users.py
├── routes/              # FastAPI routers
│   ├── products.py      # Public product endpoints
│   ├── cart.py          # Cart operations
│   ├── orders.py        # Checkout + order history
│   ├── auth.py          # Google OAuth
│   └── admin.py         # Admin product/order management
└── services/            # Business logic
    ├── product_service.py
    ├── cart_service.py
    ├── order_service.py
    └── auth_service.py

frontend/                # Next.js (separate app)
├── app/
├── components/
├── lib/
└── package.json

deploy/
├── nginx.conf
├── atelier.service      # systemd unit
├── setup.sh             # Server provisioning
└── deploy.sh            # Git pull + restart

.github/workflows/
└── ci.yml               # Lint + test + deploy
```

### Phase 1 Success Criteria

- [ ] Customer can browse products on mobile
- [ ] Customer can add items to cart without login
- [ ] Customer can complete checkout (guest or logged in)
- [ ] Admin can add/edit/deactivate products
- [ ] Admin can view and update order status
- [ ] Site loads in <2 seconds on mobile
- [ ] Deployed and accessible via HTTPS

---

## Phase 2: Add Analytics (Weeks 3–4)

**Goal:** Start collecting behavioral data. Basic business stats in admin dashboard.

The store continues working exactly as before. Analytics is added as a silent observer — async, non-blocking, failures are logged and swallowed.

### Week 3: Event Collection

| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | DuckDB setup | `analytics.db`, events table, connection management |
| 2 | Event endpoint | `POST /v1/events` (202 Accepted), in-memory queue |
| 3 | Background flush | Thread that writes queued events to DuckDB every 60s |
| 4 | Instrument frontend | Add event tracking calls to product views, cart, purchase |
| 5 | Session identity | Link anonymous sessions to users on login (DuckDB table) |

### Week 4: Admin Analytics

| Day | Task | Deliverable |
|-----|------|-------------|
| 6–7 | Analytics queries | Top products, revenue/day, conversion funnel, search terms |
| 8 | Admin dashboard | Stats page reading from DuckDB (admin-only) |
| 9 | Testing + hardening | Verify analytics failure doesn't affect Layer 1 |
| 10 | Buffer + polish | Error handling, graceful degradation, monitoring |

### Phase 2 Additions

```
app/
├── analytics/
│   ├── __init__.py
│   ├── collector.py     # In-memory queue + background flush thread
│   ├── database.py      # DuckDB connection management
│   └── queries.py       # Analytics query functions
├── models/
│   └── events.py        # Event type schemas
└── routes/
    ├── events.py        # POST /v1/events
    └── admin.py         # + analytics dashboard endpoints
```

### Phase 2 Success Criteria

- [ ] Events are collected for page views, cart actions, purchases
- [ ] Admin can see: orders/day, revenue, top products, conversion rate
- [ ] If DuckDB is deleted, the store still works perfectly
- [ ] Event collection adds <5ms to response times (fire-and-forget)

---

## Phase 3: ML Experiments (Week 5+)

**Goal:** Learn ML techniques. Ship recommendations if they actually improve conversions.

This is your sandbox. Experiment freely. The only rule: **nothing here may affect Layer 1 reliability.**

### Tasks (No Fixed Schedule)

| Task | What | Complexity |
|------|------|-----------|
| Co-occurrence | "Customers who bought X also bought Y" | Low |
| Popularity scoring | Weighted blend of views, carts, purchases | Low |
| Recommendation API | `GET /v1/recommendations?product_id=X` | Medium |
| Fallback chain | ML → popularity → featured → random | Medium |
| Pre-computation job | Background job (30min) writes recommendation cache | Medium |
| Session sequences | Track browsing paths, suggest next product | High |
| A/B testing | Measure if recommendations increase cart size | High |

### Phase 3 Additions

```
app/
├── ml/
│   ├── __init__.py
│   ├── recommender.py   # Candidate generation + ranking
│   ├── features.py      # Feature computation from DuckDB
│   └── jobs.py          # Background precomputation (APScheduler)
├── models/
│   └── recommendations.py
└── routes/
    └── recommendations.py  # GET /v1/recommendations
```

### Phase 3 Rules

- Recommendations served from pre-computed cache (SQLite table or JSON file)
- If cache is empty → show popular products (sorted by order count from SQLite)
- If that fails → show random active products
- Background computation job runs every 30 minutes
- **ML code never imported by Layer 1 route handlers**

---

## Dependency Graph

```
PHASE 1 (no dependencies — start immediately)
═══════════════════════════════════════════════

  products → cart → orders → auth → admin → frontend → deploy
  (each builds on the previous, but all are Layer 1)


PHASE 2 (depends on Phase 1 being live)
═══════════════════════════════════════════

  event-collection → analytics-queries → admin-dashboard-stats
  (independent of Layer 1 code — adds new routes, never modifies existing)


PHASE 3 (depends on Phase 2 having data)
═══════════════════════════════════════════

  features → recommender → cache → api-endpoint → frontend-widget
  (independent sandbox — reads from DuckDB, writes to cache)
```

---

## Key Decisions

| Decision | Chosen | Why |
|----------|--------|-----|
| Prices stored as | `INTEGER` (cents) | No floating point errors |
| Session storage | SQLite table + cookie | Survives server restart |
| Order items | Snapshot (name + price copied) | Price changes don't alter history |
| Admin auth | First Google OAuth user = admin | Simple bootstrap, no invite system |
| Cart key | session_id (not user_id) | Works for anonymous users, persists on login |
| Event writes | In-memory queue → DuckDB (background) | Never blocks response |
| Recommendations | Pre-computed cache, fallback chain | Never fails visibly |
| Frontend | Next.js (separate repo/dir) | Decoupled, can be replaced |

---

## What This Plan Does NOT Include

These are explicitly deferred. They are not needed for the store to work:

- ❌ Custom browser event SDK (use simple `fetch()` calls)
- ❌ JSONL buffer layer (in-memory queue is simpler)
- ❌ File-lock coordination (single-writer thread for DuckDB)
- ❌ Tiered materialized analytics tables (query DuckDB directly)
- ❌ Session expiry background job (sessions expire on read)
- ❌ GDPR tooling (handle manually if needed)
- ❌ Maintenance CLI (use SQLite CLI + simple scripts)
- ❌ CSV bulk import (admin UI is fine for <100 products)

---

## Effort Summary

| Phase | Duration | What Ships |
|-------|----------|-----------|
| Phase 1 | 2 weeks | Working e-commerce store, deployed, selling candles |
| Phase 2 | 2 weeks | Silent event collection + admin analytics dashboard |
| Phase 3 | Ongoing | ML experiments, ship when they prove value |
| **Total to revenue** | **2 weeks** | |
