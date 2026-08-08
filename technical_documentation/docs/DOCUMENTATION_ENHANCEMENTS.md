# Documentation Updates — AtelierMarie

> Generated 2026-08-08. Comprehensive technical documentation enhancements for AtelierMarie e-commerce platform.

## What Changed

### 1. **ARCHITECTURE.md** — Enhanced with API & Data Model Details

**Before:** High-level system overview (Layer 1 vs Layer 2, diagram).

**After:** 
- ✅ Expanded "Layer 1" section with **data model overview** (Products, Users, Orders, Delivery, Payments)
- ✅ Added full **Postgres schema reference** (table relationships, key design decisions)
- ✅ Detailed **data flows** for common operations (browse, add to cart, checkout, card payment)
- ✅ **Complete API surface** reference table (60+ endpoints with auth requirements)
- ✅ Identity model clarification (session-first, optional login)
- ✅ Links to `docs/API.md` for exhaustive endpoint docs

**Why:** Developers now have a complete map of the system in one place. No need to hunt through code or OpenSpec files to understand the overall architecture.

---

### 2. **API.md** (NEW) — Complete Endpoint Reference

**Purpose:** Comprehensive API documentation generated from OpenSpec changes and actual code.

**Contains:**
- ✅ **60+ endpoints** across Products, Cart, Checkout, Orders, Auth, Admin
- ✅ HTTP method, path, authentication requirements
- ✅ Request/response body examples (JSON)
- ✅ Query parameters with descriptions
- ✅ Status codes and error scenarios
- ✅ Sections: Products, Cart, Checkout & Orders, Auth, Social, Admin, Webhooks
- ✅ Error handling guide + pagination + rate limiting + localization

**Format:** Single-source-of-truth reference; can be published to Swagger/OpenAPI or shared with frontend/mobile teams.

**Example sections:**
```
POST /v1/orders — Create order (COD/bank transfer) — 201/400/409 responses
GET /v1/products — List/search products — FTS + pagination
POST /v1/admin/orders/{id}/courier/create-waybill — Create Speedy/Econt shipment
```

**Who benefits:** Frontend developers, mobile teams, API consumers, integration partners.

---

### 3. **DATABASE_SCHEMA.md** — Enhanced with Storage Architecture & Context

**Before:** Table-by-table schema reference (80+ tables, mostly structure).

**After:**
- ✅ New **"Storage Architecture"** section (multi-DB design: Postgres + DuckDB)
- ✅ **Detailed "Storage Rules"** with rationale:
  - Why money is integer cents (no floating-point errors)
  - Why product IDs are text slugs (immutability for snapshots)
  - Why timestamps are `timestamptz` (UTC consistency)
  - Why JSON payloads are `text` columns (flexibility)
  - FTS indexing strategy (localized search: en + bg)
- ✅ **Explicit isolation:** "Analytics storage is completely separate from Postgres"
- ✅ Cross-references to `ARCHITECTURE.md` for data flows

**Why:** New developers understand not just *what* tables exist, but *why* they're designed this way and what constraints they must respect.

---

### 4. **ONBOARDING.md** — Massively Expanded with Workflows & Patterns

**Before:** Setup instructions, Makefile targets, troubleshooting.

**After:** 
- ✅ **Enhanced "Start Here"** with 10 key facts (architecture, ports, default modes)
- ✅ **"Development Workflows"** section (8 common scenarios):
  - Add a new product attribute
  - Fix a bug (locating → testing → committing)
  - Add an admin feature
  - Debug Stripe payments
  - Test Stripe/Econt locally
  - Add backend/frontend tests
- ✅ **"How Services Are Organized"** (thin routes, fat services pattern with example code)
- ✅ **"Architecture Decision Records"** (why we chose Postgres, sessions-first, prices as cents, etc.)
- ✅ **"Key Constraints & Safety Checks"** (7 rules to never break: Layer 1 isolation, stock validation, immutable orders, etc.)
- ✅ **"Good First Tasks"** (8 beginner-friendly items, 6 to avoid)
- ✅ **"Performance Tips"** + **"Documentation Map"** (which doc to read for what)
- ✅ **"Common Checks"** (pre-commit verification commands)

**Why:** New developers no longer feel lost. Workflows guide them through real scenarios (bug fixes, feature additions, debugging). Safety checks prevent architectural mistakes.

---

## How These Docs Connect

```
ONBOARDING.md (entry point)
  └─ "Start Here" → understand local setup & key facts
  └─ "Development Workflows" → guides for common tasks
     └─ Points to ARCHITECTURE.md for context
     └─ Points to docs/API.md for endpoint details
     └─ Points to docs/DATABASE_SCHEMA.md for data model

ARCHITECTURE.md (system overview)
  └─ Layer 1 vs Layer 2 design
  └─ Data model overview
  └─ API surface reference → links to docs/API.md
  └─ Data flows → clarifies what hits DB when

docs/API.md (endpoint reference)
  └─ Exhaustive endpoint docs
  └─ Request/response examples
  └─ Error codes & pagination
  └─ Can be auto-published to Swagger

docs/DATABASE_SCHEMA.md (data definition)
  └─ Every table, column, index, FK
  └─ Storage rules with rationale
  └─ Startup migrations & seeds
  └─ Courier admin schema notes

CLAUDE.md (checked in — project rules)
  └─ Coding standards
  └─ Layer separation rules
  └─ Testing requirements
  └─ Code review checklist

openspec/changes/*/design.md (feature specs)
  └─ Context for specific features
  └─ Data model changes for that feature
  └─ Why a feature was built a certain way
```

---

## What You Should Know

### These Docs Are Now The Source of Truth For

- **What endpoints exist** (docs/API.md)
- **How data flows through the system** (ARCHITECTURE.md)
- **What the database schema is** (DATABASE_SCHEMA.md)
- **How to onboard new developers** (ONBOARDING.md)
- **Why certain architectural choices were made** (ARCHITECTURE.md + CLAUDE.md)

### These Docs Are NOT For

- **Specific feature history** — that's in `openspec/changes/*/design.md`
- **Current in-progress work** — that's in git branches and PRs
- **Deployment procedures** — that's in separate ops docs (future)

### Keep These In Sync

1. **When adding a new table:** Update `docs/DATABASE_SCHEMA.md` + `docs/API.md` (if it has a public endpoint)
2. **When adding a new route:** Update `docs/API.md` + `ARCHITECTURE.md` (if it changes the overall system picture)
3. **When changing an auth pattern or identity model:** Update `ARCHITECTURE.md` + `ONBOARDING.md`
4. **When adding a workflow or common task pattern:** Update `ONBOARDING.md` "Development Workflows" section

---

## Testing The Docs

**Quick verify:**
1. Pick a random endpoint from `docs/API.md` (e.g., `POST /v1/cart`)
2. Find it in the code (e.g., `app/routes/cart.py`)
3. Confirm request/response matches the docs
4. If it doesn't, the docs are stale — fix them

**Manual test:**
1. Read ONBOARDING.md "First Setup" section
2. Follow the steps
3. Run a local API call: `curl http://localhost:8000/v1/products`
4. Confirm response shape matches `docs/API.md` → "List/Search Products"

---

## Next Steps (Optional)

These docs are now complete for current state. Future enhancements:

- **OpenAPI/Swagger generation:** Extract `docs/API.md` into OpenAPI 3.0 spec (`openapi.yaml`), generate Swagger UI
- **GraphQL schema:** If adding GraphQL layer, document schema in `docs/GRAPHQL.md`
- **Deployment & Ops:** Create `docs/DEPLOYMENT.md` (CI/CD, production setup, monitoring)
- **Troubleshooting guide:** Expand ONBOARDING.md "Troubleshooting" section with more edge cases
- **Video walkthroughs:** Record 2-3 min videos for "Onboarding Workflows" (add product, debug order, etc.)

---

## Files Modified

| File | Changes |
|------|---------|
| `docs/ARCHITECTURE.md` | +200 lines: data model, API reference, expanded Layer 1 section |
| `docs/API.md` | +800 lines: NEW comprehensive endpoint reference (60+ endpoints) |
| `docs/DATABASE_SCHEMA.md` | +50 lines: Storage architecture, rules with rationale |
| `docs/ONBOARDING.md` | +400 lines: Workflows, patterns, constraints, safety checks, decision records |

**Total:** ~1,450 new/modified lines across 4 docs.

---

## Questions?

- **What's the API endpoint for X?** → `docs/API.md`
- **How does checkout work?** → `ARCHITECTURE.md` → "Checkout Data Flow"
- **Why is product ID a slug?** → `docs/DATABASE_SCHEMA.md` → "Storage Rules"
- **How do I add a feature?** → `ONBOARDING.md` → "Development Workflows"
- **What are the coding rules?** → `CLAUDE.md` (checked in)
