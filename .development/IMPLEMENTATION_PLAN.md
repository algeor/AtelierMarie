# Atelier Marie — Implementation Plan

> Two developers working in parallel. Ship the store in 2 weeks.

## Philosophy

**Phase 1 is the product. Phases 2 and 3 are learning exercises.**

The split is designed so that:
- **Dev A (Backend)** and **Dev B (Frontend)** can work independently 90% of the time
- They agree on contracts (API shapes) on Day 1, then diverge
- Dev B can mock the API and build the full UI without waiting for Dev A
- Sync points are minimal and well-defined

---

## Developer Assignment

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PARALLEL DEVELOPMENT MAP                           │
│                                                                      │
│  Dev A (Backend + API + Deploy)        Dev B (Frontend + Design)     │
│  ══════════════════════════════        ═══════════════════════════   │
│                                                                      │
│  Day 1:  Shared setup (together)       Day 1: Shared setup (together)│
│  Day 2:  Product catalog API           Day 2: Next.js init + design  │
│  Day 3:  Session + Cart API            Day 3: Product pages          │
│  Day 4:  Orders + Checkout API         Day 4: Cart + Checkout UI     │
│  Day 5:  Auth + Image upload           Day 5: Auth UI + Account      │
│  Day 6:  Admin API + polish            Day 6: Admin UI               │
│  Day 7:  Integration testing           Day 7: Integration testing    │
│  Day 8:  Deployment setup              Day 8: Polish + responsive    │
│  Day 9:  Deploy + CI/CD               Day 9: Connect to real API     │
│  Day 10: Go live (together)            Day 10: Go live (together)    │
│                                                                      │
│  Sync Points: ★ Day 1 (contracts)  ★ Day 7 (integration)  ★ Day 10 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ★ Day 1: Shared Setup (Both Devs Together)

This is the ONE day you must work together. Agree on all contracts upfront.

### Shared Deliverables

| File | What to Agree On |
|------|-----------------|
| `pyproject.toml` | All dependencies (fastapi, uvicorn, pydantic, pyjwt, httpx, pillow, duckdb) |
| `app/config.py` | All env vars (DB path, JWT secret, OAuth creds, admin key, analytics flag) |
| `app/database.py` | SQLite connection factory, WAL init, schema creation |
| `app/main.py` | App factory, lifespan, router registration pattern |
| `app/models/*.py` | **All Pydantic schemas** — this is the API contract Dev B builds against |
| `conftest.py` | Shared test fixtures (test DB, test client) |
| `frontend/lib/types.ts` | TypeScript types matching the Pydantic models exactly |

### The Critical Contract: API Response Shapes

Dev B builds the entire frontend against these shapes. Define them on Day 1:

```python
# app/models/products.py
class ProductResponse(BaseModel):
    id: str
    name: str
    description: str | None
    price_cents: int
    category: str | None
    image_url: str | None  # "/static/products/{id}.webp" or None
    stock: int
    is_active: bool
    is_featured: bool

class ProductListResponse(BaseModel):
    products: list[ProductResponse]
    total: int
    page: int
    limit: int

# app/models/cart.py
class CartItemResponse(BaseModel):
    product_id: str
    product: ProductResponse
    quantity: int
    added_at: str

class CartResponse(BaseModel):
    items: list[CartItemResponse]
    total_cents: int
    item_count: int

# app/models/orders.py
class OrderResponse(BaseModel):
    id: str
    status: str  # pending | confirmed | shipped | delivered | cancelled
    total_cents: int
    customer_email: str
    items: list[OrderItemResponse]
    created_at: str

# app/models/users.py
class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None
    avatar_url: str | None
    is_admin: bool
```

Once these are agreed, Dev B creates `frontend/lib/mock-api.ts` with hardcoded responses matching these shapes and builds the entire UI against mocks.

---

## Dev A: Backend + API + Deploy

### [DONE] Day 2: Product Catalog

- [X] Define `products` table schema (text PK as SKU/slug, price_cents, stock CHECK >= 0)
- [X] Create `app/services/product_service.py` (list, get, create, update, deactivate, search)
- [X] Create `app/routes/products.py` (public GET: list with filters, search, pagination, detail)
- [X] Create `app/routes/admin.py` (POST/PUT/DELETE products, CSV bulk import)
- [X] Implement CSV import: streaming parse, upsert semantics, error reporting
- [X] Write tests for product service
- [X] Seed script with ~10 sample candle products

### [DONE] Day 3: Session + Cart

- [x] Define `sessions` and `cart_items` table schemas
- [x] Create `app/middleware/session.py` (cookie creation/validation, sliding 30-day expiry)
- [x] Create `app/services/cart_service.py` (get_cart, add_item, update_quantity, remove_item)
- [x] Stock validation on add (immediate 409 if insufficient)
- [x] Quantity limits (max 10 per item, max 20 distinct items)
- [x] Create `app/routes/cart.py` (GET/POST/PATCH/DELETE)
- [x] Write tests (stock validation, limits, update-to-zero = remove)

### [DONE] Day 4: Orders + Checkout

- [X] Define `orders` and `order_items` table schemas
- [X] Create `app/services/order_service.py` (checkout, list, get, update_status)
- [X] Implement atomic checkout (validate → transaction → snapshot prices → decrement stock → clear cart)
- [X] Implement order state machine (valid transitions only, 422 on invalid)
- [X] Stock restoration on cancellation
- [X] Create `app/routes/orders.py` (POST, GET list, GET detail)
- [X] Admin order routes (list all, update status)
- [X] Write tests (happy path, out-of-stock, race condition, cancel restores stock)

### Day 5: Authentication + Image Upload

- [ ] Define `users` table schema
- [ ] Create `app/services/auth_service.py` (OAuth via httpx, JWT, JWKS cache, first-admin)
- [ ] Create `app/routes/auth.py` (login, callback, me, logout)
- [ ] Dual admin auth (JWT is_admin OR API key)
- [ ] Session rotation on logout (X-Session-Rotated header)
- [ ] Create `app/services/image_service.py` (validate, resize, WebP convert via Pillow)
- [ ] Create `POST /v1/admin/products/{id}/image` (multipart upload, max 5MB)
- [ ] Write tests (mock OAuth, first-admin bootstrap, image processing)

### Day 6: Admin Polish + Edge Cases

- [ ] `GET /v1/admin/dashboard` (basic stats: order count, revenue, product count from SQLite)
- [ ] Pagination on all list endpoints
- [ ] Error responses (consistent format: `{error, detail}`)
- [ ] Input validation edge cases (empty strings, negative prices, huge quantities)
- [ ] Rate limiting config for Nginx (auth + checkout endpoints)
- [ ] API docs polish (FastAPI auto-docs, descriptions on all endpoints)

### Day 7: Integration Testing ★

- [ ] End-to-end test: browse → add to cart → checkout → verify order
- [ ] End-to-end test: login → link session → view orders
- [ ] End-to-end test: admin CRUD products + upload image
- [ ] Fix any issues found during Dev B's integration
- [ ] Verify session cookie works cross-origin (CORS config for Next.js dev server)

### Day 8–9: Deployment

- [ ] Create `deploy/nginx.conf` (proxy /v1/ → :8000, / → :3000, /static/ → disk, SSL)
- [ ] Create `deploy/atelier-api.service` (systemd, uvicorn --workers 2)
- [ ] Create `deploy/atelier-frontend.service` (systemd, next start)
- [ ] Create `deploy/setup.sh` (provision VPS: Python 3.11, Node.js, Nginx, certbot)
- [ ] Create `deploy/deploy.sh` (git pull, install, build, restart)
- [ ] Create `.github/workflows/ci.yml` (lint, test, deploy on push to main)
- [ ] Create `deploy/backup.sh` (daily SQLite backup, 7-day retention)
- [ ] Deploy and verify end-to-end on VPS

### Day 10: Go Live ★

- [ ] Final smoke test on production
- [ ] DNS + SSL setup
- [ ] Upload real product photos
- [ ] Seed production database with real product catalog

---

## Dev B: Frontend + Design

### [Done] Day 2: Project Init + Design System

- [x] Init Next.js 14 project in `frontend/` (App Router, TypeScript, Tailwind)
- [x] Create design tokens in Tailwind config (colors: warm-ivory, cream, champagne-beige, dusty-pink, soft-brown, charcoal, muted-gold)
- [x] Set up typography (Playfair Display headings, Inter body)
- [x] Create `frontend/lib/types.ts` (from Day 1 contracts)
- [x] Create `frontend/lib/mock-api.ts` (hardcoded responses matching contract shapes)
- [x] Create `frontend/lib/api.ts` (real fetch wrapper — switch from mock when backend ready)
- [x] Build base UI components: Button (primary/secondary/ghost), Input, Badge, Skeleton

### [DONE] Day 3: Product Pages

- [x] Global layout (Header with logo + nav + cart icon, Footer with links)
- [x] Announcement bar (dismissible, session-persistent)
- [x] Homepage: hero section + featured products grid
- [x] Product listing page (`/products`): grid (4-col/2-col/1-col responsive), category filter pills
- [x] Product detail page (`/products/[id]`): image, name, price, description, quantity selector, Add to Cart button
- [x] Product image display with `next/image` (lazy load, responsive srcset)
- [x] CSS placeholder for products without images (gradient + product name)

### [DONE] Day 4: Cart + Checkout

- [x] Cart context (React Context for state: items, total, count)
- [x] Cart drawer (slide-in from right, overlay, item list, quantity controls, remove, subtotal)
- [x] Cart badge in header (live item count)
- [x] Add-to-cart interaction (button → brief checkmark animation → badge update → optional drawer open)
- [x] Checkout page: contact form (email, name), shipping address, order summary sidebar
- [x] Form validation (required fields, email format)
- [x] Order confirmation page (order ID, items, total, "thank you" message)

### Day 5: Auth + Account

- [] Login button in header (redirects to `/v1/auth/login`)
- [] Handle OAuth callback redirect (user lands back on site, JWT cookie set)
- [] Account page: show user info (name, email) or login prompt if anonymous
- [] My Orders page: list of past orders with status badges
- [] Order detail page: items, total, status timeline
- [] Handle `X-Session-Rotated` header in API client (update local state on logout)

### Day 6: Admin UI

- [X] Admin layout (separate nav: Dashboard, Products, Orders)
- [X] Admin dashboard: stats cards (orders today, revenue this week, product count)
- [X] Admin product list: table with edit/deactivate actions
- [X] Admin product form: create/edit (name, description, price, category, stock, image upload)
- [X] Admin order list: table with status filter, status update dropdown
- [X] Protect admin routes (redirect to login if not admin)

### Day 7: Integration ★

- [ ] Switch from `mock-api.ts` to real `api.ts` (point to Dev A's running backend)
- [ ] Fix any response shape mismatches
- [ ] Test full flow: browse → cart → checkout → order confirmation
- [ ] Test auth flow: login → account page → my orders
- [ ] Test admin flow: add product → upload image → verify on storefront
- [ ] Fix CORS / cookie issues (session cookie must work cross-origin in dev)

### Day 8: Polish + Responsive

- [ ] Mobile responsive pass on all pages (test at 375px, 768px, 1024px)
- [ ] Mobile navigation (hamburger menu → slide-in drawer)
- [ ] Touch targets (44px minimum, 8px spacing)
- [ ] Loading states (Skeleton components on all data-fetching pages)
- [ ] Error states (network error, 404 product, empty cart, out-of-stock on checkout)
- [ ] SEO (meta tags, Open Graph, proper heading hierarchy)
- [ ] Accessibility (alt text, aria labels, keyboard navigation, focus management)

### Day 9: Final Polish

- [ ] Search overlay (full-screen, autofocus, 300ms debounce, results as-you-type)
- [ ] Performance: ensure Lighthouse score >90 (LCP <2.5s on mobile)
- [ ] Static pages: Candle Care, FAQ, Contact form
- [ ] Newsletter signup component (email → can be wired to anything later)
- [ ] Favicon + brand assets
- [ ] 404 page

### Day 10: Go Live ★

- [ ] Final visual review on production URL
- [ ] Mobile test on real device
- [ ] Verify images load correctly via Nginx
- [ ] Social sharing preview (Open Graph image)

---

## Interface Contract (How the Devs Stay Independent)

### The Rule

> **Dev B builds against mock data from Day 2–6. Dev B only connects to the real API on Day 7.**

This means Dev A can iterate freely on implementation details (SQL queries, error handling, edge cases) without blocking Dev B. As long as the response shapes from Day 1 don't change, both devs stay independent.

### Shared Files (Touch Points)

| File | Owner | Consumer | Rule |
|------|-------|----------|------|
| `app/models/*.py` | Dev A | Dev B (via types.ts) | Frozen after Day 1 (changes need sync) |
| `frontend/lib/types.ts` | Dev B | Dev B | Must match models exactly |
| `app/config.py` | Dev A | Both | Dev A adds vars; Dev B reads via API |
| `app/main.py` | Dev A | — | Dev A registers routers |
| `deploy/*` | Dev A | Both | Dev A owns infra |
| `frontend/*` | Dev B | — | Dev B owns all frontend code |

### What If the Contract Needs to Change?

1. Dev A pings Dev B: "I need to add a `thumbnail_url` field to ProductResponse"
2. Dev B updates `types.ts` and `mock-api.ts`
3. Both continue independently
4. Takes 5 minutes — no blocking

---

## Phase 2: Analytics (Week 3–4, after store is live)

### Dev A: Backend Analytics

| Day | Task |
|-----|------|
| 1 | DuckDB + JSONL setup, analytics module scaffold |
| 2 | Batch loader (JSONL → DuckDB, background thread) |
| 3 | Event endpoint (POST /v1/events) + models |
| 4 | Instrument backend routes (fire-and-forget event emission) |
| 5 | Admin analytics queries (revenue, top products, funnel) |
| 6 | Analytics API endpoints (GET /v1/admin/analytics) |
| 7 | Hardening (graceful degradation, rebuild CLI, archive rotation) |
| 8 | Load testing + monitoring |

### Dev B: Frontend Analytics

| Day | Task |
|-----|------|
| 1 | Create `lib/analytics.ts` (buffer + flush + sendBeacon) |
| 2 | Instrument page_view tracking on product pages |
| 3 | Verify events flowing (check JSONL files) |
| 4 | Admin analytics page (tables showing metrics from API) |
| 5 | Polish analytics dashboard (add date range picker, export) |
| 6–8 | Help Dev A with integration testing / start Phase 3 ML research |

---

## Phase 3: ML Experiments (Week 5+, no deadline)

Single developer (either one) works on this when ready. Not parallelizable — it's a learning sandbox.

---

## Effort Summary

| Phase | Duration | Dev A | Dev B | Outcome |
|-------|----------|-------|-------|---------|
| Phase 1 | 2 weeks | Backend + API + Deploy | Frontend + Design | **Store is live, selling candles** |
| Phase 2 | 1.5 weeks | Analytics backend | Analytics frontend | Silent event collection + admin stats |
| Phase 3 | Ongoing | — | — | ML experiments (one dev at a time) |
| **Total to revenue** | **2 weeks** | | | |

---

## Risk Mitigation

| Risk | How We Avoid It |
|------|-----------------|
| Contract mismatch between frontend/backend | Define all Pydantic models on Day 1; Dev B generates TypeScript types from them |
| Dev B blocked waiting for API | Mock API from Day 1; integrate on Day 7 only |
| Merge conflicts | Dev A owns `app/`, Dev B owns `frontend/`. Shared files (config, models) change rarely after Day 1 |
| Integration day disasters | Day 7 is a full buffer day for fixing issues before deploy |
| Session cookies don't work cross-origin in dev | Dev A configures CORS on Day 2; Dev B sets `credentials: 'include'` in mock-api |
| One dev finishes early | Dev A can help with frontend components; Dev B can help write backend tests |
