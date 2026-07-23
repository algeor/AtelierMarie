## Context

Product management already exists end-to-end (admin CRUD API, admin form, CSV import), but its three surfaces have drifted apart:

- The **model** supports `is_active` on create/update, but the **edit form** never exposes it — it's only togglable from the list table.
- **CSV import** parses a subset of columns and silently ignores `is_featured`, `materials`, `days_to_craft`, and `is_active` even though the model accepts them.
- Products have **no shipping weight** at all. `weight_grams` is already designed in `shipping-courier-integration/design.md` Decision 13 and referenced by `shipping-pricing`, but bundled with courier-API work that is blocked on live Speedy/Econt accounts.

This change closes the drift and lands the `weight_grams` data half independently. It is admin-only and touches no customer-facing or checkout code.

## Goals / Non-Goals

**Goals:**
- Add `weight_grams` to the DB, admin models, admin form, and CSV import.
- Expose `is_active` in the edit form.
- Make CSV import cover every field the form/model supports.
- Keep the change safe: no cart/checkout/pricing/public-API impact.

**Non-Goals:**
- Shipping cost calculation or courier APIs (stays in `shipping-pricing`).
- Exposing weight to customers (public `ProductResponse` unchanged).
- Promotional discounts (Change B), dynamic categories (Change C), multiple images (Change D).

## Decisions

### 1. `weight_grams INTEGER NOT NULL DEFAULT 300`
Adopt Decision 13's column definition verbatim. 300g is a safe middle for candles (range ~150–800g); courier APIs tolerate ±200g, so imprecise defaults are acceptable and refineable. `NOT NULL DEFAULT 300` means existing rows backfill to 300 during the table rebuild (see Decision 3).

The Pydantic bound is a **local** constant `MAX_WEIGHT_GRAMS` in `app/models/products.py`, mirroring how that module already defines its own local `MAX_STOCK = 99999` (note: `app/constants.py` has a *different* `MAX_STOCK = 999_999` — the models module intentionally uses its own, so `weight_grams` follows the local-constant pattern rather than importing from `constants.py`). Proposed value `MAX_WEIGHT_GRAMS = 100_000` (100 kg — generous headroom over the ~800g max real candle). Field bound: `ge=1, le=MAX_WEIGHT_GRAMS` (a physical product weighs at least 1g).

**Alternative considered:** nullable weight with runtime fallback. Rejected — pushes the default into every read site and complicates the shipping calc later.

### 2. Exclude `weight_grams` from public `ProductResponse` (deviation from Decision 13)
Decision 13 listed `ProductResponse.weight_grams`. We deviate: weight is a shipping *input* the customer chose not to see (explicit product decision). The shipping calculator reads weight server-side directly from `products`, so it never needs the value in the public JSON. Keeping it out avoids leaking a logistics detail and keeps the public contract minimal.

**Trade-off:** if a future feature wants to show weight to customers, add it to `ProductResponse` then — cheap and non-breaking.

### 3. Migration: four order-synchronized edits in `app/database.py`
Products are **not** migrated with `ALTER TABLE ADD COLUMN`. `init_db()` runs `_migrate_existing_schema()` first; `_migrate_products_table()` rebuilds the table via a `products_new` copy, and **short-circuits when `columns == set(_PRODUCT_COLUMNS)`** (already-migrated DBs skip; DBs missing `weight_grams` trigger the rebuild). Adding `weight_grams` therefore requires **four edits that must stay in the same column order**:

1. `_SCHEMA_SQL` — `CREATE TABLE IF NOT EXISTS products` (fresh DBs).
2. `_PRODUCTS_TABLE_SQL` — the `products_new` rebuild table.
3. `_PRODUCT_COLUMNS` — the tuple used for both the INSERT column list and the equality guard.
4. `select_exprs` in `_migrate_products_table()` — add `_column_expr(columns, "weight_grams", "300")` so old rows without the column backfill to literal `300`.

The `INSERT INTO products_new (_PRODUCT_COLUMNS) SELECT (select_exprs)` is positional: `weight_grams` must sit at the **same index** in `_PRODUCT_COLUMNS`, `select_exprs`, and the `_PRODUCTS_TABLE_SQL` column order. Insert it consistently (e.g. right after `stock`). FTS triggers reference only name/description/category, so `weight_grams` doesn't touch the FTS rebuild.

### 4. CSV import: parser-only for existing fields; service change only for `weight_grams`
Key realization from the code: `product_service.upsert_product()` and `update_product()` already carry `materials`, `days_to_craft`, `is_active`, and `is_featured` in their `field_map`. CSV silently drops them **only because the parser never puts them in the `data` dict** — the service already persists them. So "complete CSV import" is:

- **Parser-only** (`app/routes/admin.py`) for `materials`, `days_to_craft`, `is_active`, `is_featured`: read the column when present, validate, add to `data` — mirroring the existing `category`/`image_url`/`stock` blocks. Booleans (`is_active`/`is_featured`) need a new case-insensitive helper accepting `true/false/1/0/yes/no`; anything else is a per-row error (so a typo can't silently deactivate a product). `days_to_craft` validates as int like `stock`.
- **Parser + service** for `weight_grams`: parse/validate in the route, add `weight_grams` to the `field_map` in `upsert_product`/`update_product` and to the explicit `columns`/`values` in `create_product` (use `data.get("weight_grams", 300)` for direct callers).

**Default semantics (precise):** a *missing* `weight_grams` column relies on the DB `DEFAULT 300` — which applies to **newly-created** rows only. Upserting an **existing** product without the column leaves its weight unchanged (the field isn't in `field_map`'s update set). This is correct and is reflected in the spec scenarios.

### 5. `is_active` in the form is just another field
The `UpdateProductRequest`/`CreateProductRequest` already accept `is_active`. The form adds a toggle bound to `formData.is_active` and includes it in the submit payload. No API change. The list-table toggle stays as a convenience shortcut.

## Risks / Trade-offs

- **CSV boolean ambiguity** → define an explicit accepted-values set and reject others as a row error, so a typo can't silently deactivate a product.
- **Migration edits drift out of order** → the four locations in Decision 3 are positional; if `select_exprs` and `_PRODUCT_COLUMNS` disagree in order, the rebuild silently maps values to the wrong columns. Tasks call out the exact four edits + shared index.
- **`create_product` uses an explicit values list** (not `field_map`) → `weight_grams` must be added to both its `columns` and `values` lists at the matching position, separately from the `upsert`/`update` `field_map`.
- **Spec conflict with `shipping-pricing`** (both claiming `weight_grams`) → annotate `shipping-pricing` that the data half moved here; it only consumes the field.
- **Weight defaults are approximate** → acceptable per Decision 13; admin can refine per product over time.

## Migration Plan

1. Apply the four order-synchronized edits (Decision 3). Fresh DBs get the column from `_SCHEMA_SQL`; existing DBs get it via the `products_new` rebuild, backfilled to 300.
2. Ship model + service + CSV + form together (single change).
3. Rollback: the column is additive with a safe default; reverting code leaves a harmless unused column. No destructive migration.

## Open Questions

- None blocking. (Whether to later surface weight to customers is deferred, not part of this change.)
