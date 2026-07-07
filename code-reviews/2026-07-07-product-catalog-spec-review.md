# Product Catalog OpenSpec — Design Review

**Date:** 2026-07-07  
**Target:** `openspec/changes/product-catalog/`  
**Reviewer:** Claude  
**Verdict:** 🔴 3 critical issues must be resolved before implementation

---

## 🔴 Critical — Will Cause Bugs at Implementation

### 1. `INSERT OR REPLACE` contradicts "merge only CSV columns"

**Location:** `design.md` Decision #5 + Risks table

The design says:
> Upsert valid rows using `INSERT OR REPLACE` in batches of 100

But then in Risks:
> `INSERT OR REPLACE` drops columns not in CSV — CSV import explicitly handles this — fetches existing row first, merges only CSV-provided columns.

These contradict each other. `INSERT OR REPLACE` in SQLite **deletes the existing row and inserts a new one**. If the CSV doesn't include `is_active`, `is_featured`, `materials`, `days_to_craft`, or `image_url`, those fields get wiped to their DEFAULT values. The mitigation describes a SELECT-then-UPDATE pattern — which is fundamentally different from `INSERT OR REPLACE`.

**Fix:** Change the decision to use SQLite's `INSERT INTO ... ON CONFLICT(id) DO UPDATE SET ...` (UPSERT syntax, available since SQLite 3.24+) or explicitly describe the SELECT → merge → conditional INSERT/UPDATE pattern. Update tasks 7.4 accordingly.

---

### 2. Seed script idempotency impossible with `create_product` (rejects duplicates)

**Location:** `specs/product-seed/spec.md` vs `specs/product-service/spec.md`

The seed spec says:
> Idempotent (safe to run multiple times — uses upsert semantics)

> The seed script SHALL import and use the product service (not raw SQL)

But the product-service spec says:
> `create_product` SHALL reject creation if a product with the same ID already exists (DuplicateError)

There is no `upsert_product` method in the service spec. The seed script **cannot** be idempotent using `create_product` alone — second run always fails with DuplicateError for every product.

**Fix:** Either:
- (a) Add an `upsert_product(data)` method to the product-service spec (INSERT or UPDATE by ID), or
- (b) Explicitly specify that the seed script catches `DuplicateError` and calls `update_product` as fallback, or
- (c) Allow the seed to use `deactivate` + re-create (ugly, don't do this)

Option (a) is cleanest — an upsert method is also needed for the CSV import logic.

---

### 3. `price_cents` rename task omits `ProductResponse` and frontend types

**Location:** `tasks.md` Task 2.1 vs `proposal.md`

The proposal says:
> Align `ProductResponse.price` field name to `price_cents`

Task 2.1 says:
> Rename `price` → `price_cents` in `CreateProductRequest` and `UpdateProductRequest`

But **does not mention** renaming in:
- `ProductResponse` (has `price: int` on line 14 of `app/models/products.py`)
- `OrderItemResponse` in `app/models/orders.py` (has `price: int`)
- `CartResponse.total` (should this be `total_cents`?)
- `frontend/lib/types.ts` (has `price: number`)
- `frontend/lib/mock-api.ts` (uses `price: 3200` etc.)

If only the request models are renamed but response models keep `price`, the API has an asymmetric contract — admin sends `price_cents` but receives `price` back.

**Fix:** Task 2.1 should explicitly rename in `ProductResponse`, and add a task to update frontend TypeScript types and mock data. Decide whether `OrderItemResponse.price` and `CartResponse.total` also get the `_cents` suffix for consistency.

---

## 🟡 Medium — Design Gaps

### 4. Empty `admin_api_key` default grants admin access

**Location:** `app/config.py` line 25 + `specs/product-admin-api/spec.md`

The config has `admin_api_key: str = ""`. The spec says the auth dependency checks `Bearer <ATELIER_ADMIN_API_KEY>`. If the key is empty and someone sends `Authorization: Bearer ` (empty value), the comparison `"" == ""` succeeds → admin access to anyone.

The spec has no scenario covering this case.

**Fix:** Add to the `require_admin` logic: if `settings.admin_api_key` is falsy (empty string), deny all API-key-based access. Add a spec scenario:
> WHEN admin_api_key is not configured (empty) AND a request is made with an empty Bearer token  
> THEN the response is 401

---

### 5. FTS5 trigger + INSERT OR REPLACE interaction unspecified

**Location:** `design.md` Decision #3 + `tasks.md` 1.3–1.4

The tasks specify:
- 1.3: Create FTS5 virtual table
- 1.4: Create triggers to sync on INSERT, UPDATE, DELETE
- 7.4: Upsert via INSERT OR REPLACE

`INSERT OR REPLACE` fires a DELETE trigger then an INSERT trigger. With a TEXT primary key and an FTS5 table, the implementer needs to know:
- Is `products_fts` a **content table** (`content='products'`, `content_rowid='rowid'`)? If so, triggers are unnecessary — but TEXT PKs don't have stable rowids.
- Or is it **standalone** with manual sync? Then triggers must handle the id-to-rowid mapping.

**Fix:** Specify in design.md whether to use:
- (a) `content=''` (contentless FTS5) — stores only the index, queries join back to products table by id. Simplest.
- (b) `content='products'` with external content — requires rowid alignment.
- (c) Standalone with manual triggers.

Recommendation: (a) contentless FTS5 is the simplest for a text-PK table.

---

### 6. Missing `GET /v1/admin/products/{id}` endpoint

**Location:** `specs/product-admin-api/spec.md` + `tasks.md` section 6

The service spec defines `get_product_admin(product_id)` (returns any product including inactive). But:
- The admin-api spec has no requirement for `GET /v1/admin/products/{product_id}`
- The tasks section 6 has no task for this endpoint
- The proposal lists only 6 endpoints — doesn't include admin GET single

Without this, admins cannot view details of a specific inactive product (e.g., to re-activate it). The deprecated v1 spec had this endpoint.

**Fix:** Add a requirement to `product-admin-api/spec.md` and a task to section 6.

---

### 7. `q` search param and `sort` interaction undefined

**Location:** `specs/product-public-api/spec.md`

The spec says:
- `q` triggers FTS5 search "sorted by relevance"
- `sort` can be `price_asc`, `price_desc`, `name`, `newest`

What happens when `GET /v1/products?q=lavender&sort=price_asc` is called? Does `sort` override FTS5 relevance? Or is `sort` ignored when `q` is present?

**Fix:** Add a scenario:
> WHEN `q=lavender` and `sort=price_asc` are both provided  
> THEN [choose: sort overrides relevance / sort is ignored when q is present / results are filtered by relevance then sorted by price]

---

## 🟢 Minor — Consistency/Polish

### 8. DB schema missing `materials` and `days_to_craft` columns

**Location:** `app/database.py` schema vs `app/models/products.py`

The current `_SCHEMA_SQL` in `database.py` does NOT define `materials` or `days_to_craft` columns, but `ProductResponse` has both fields. Task 1.2 correctly adds them, but design.md never mentions this existing gap or that it needs fixing.

**Impact:** Low — task covers it, just not documented in design rationale.

---

### 9. Category names don't match storefront filter UI

**Location:** `specs/product-seed/spec.md` vs `openspec/changes/core-ecommerce/specs/storefront-layout.md`

Seed spec categories: `dessert, luxury, gift, seasonal`  
Storefront filter pills: `All | Dessert | Luxury Jar | Gift Set`

"luxury" vs "Luxury Jar" and "gift" vs "Gift Set" — the seed data won't match what the frontend filters expect.

**Fix:** Define canonical category slugs once (e.g., in design.md) and reference them consistently: `dessert`, `luxury-jar`, `gift-set`, `seasonal`. Update seed spec and storefront spec to align.

---

## Summary Table

| # | Severity | Issue | Location |
|---|----------|-------|----------|
| 1 | 🔴 Critical | `INSERT OR REPLACE` contradicts merge semantics | design.md #5 |
| 2 | 🔴 Critical | Seed idempotency impossible — no upsert in service | product-seed + product-service specs |
| 3 | 🔴 Critical | `price_cents` rename misses ProductResponse + frontend | tasks.md 2.1 |
| 4 | 🟡 Medium | Empty admin_api_key default grants access | product-admin-api spec |
| 5 | 🟡 Medium | FTS5 + INSERT OR REPLACE trigger interaction | design.md #3 + tasks 1.3-1.4 |
| 6 | 🟡 Medium | Missing GET /v1/admin/products/{id} | product-admin-api spec + tasks |
| 7 | 🟡 Medium | q + sort param interaction undefined | product-public-api spec |
| 8 | 🟢 Minor | DB schema missing columns (task covers it) | tasks.md 1.2 |
| 9 | 🟢 Minor | Category names misaligned with storefront | product-seed spec |

---

## Recommended Actions

1. **Resolve upsert strategy** — pick `ON CONFLICT ... DO UPDATE` (SQLite UPSERT) as the single pattern for both CSV import and seed script. Add `upsert_product` to service spec.
2. **Complete the rename** — propagate `price_cents` to ProductResponse, OrderItemResponse, frontend types, and mock data. Decide on `total_cents` too.
3. **Guard empty API key** — add falsy check to require_admin spec.
4. **Specify FTS5 variant** — contentless is simplest for text-PK tables.
5. **Add missing admin detail endpoint.**
6. **Define q+sort precedence.**
7. **Align category slugs** across specs.
