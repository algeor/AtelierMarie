## 1. Database schema (`app/database.py`) — four order-synchronized edits

- [ ] 1.1 Add `weight_grams INTEGER NOT NULL DEFAULT 300` to `_SCHEMA_SQL` (`CREATE TABLE IF NOT EXISTS products`), positioned right after `stock`
- [ ] 1.2 Add the identical column at the same position to `_PRODUCTS_TABLE_SQL` (the `products_new` rebuild table)
- [ ] 1.3 Add `"weight_grams"` to the `_PRODUCT_COLUMNS` tuple at the matching index (drives both the INSERT column list and the `columns == set(_PRODUCT_COLUMNS)` rebuild guard)
- [ ] 1.4 Add `_column_expr(columns, "weight_grams", "300")` to `select_exprs` in `_migrate_products_table()` at the same index — old rows without the column backfill to 300
- [ ] 1.5 Verify positional alignment: `weight_grams` sits at the same index in `_PRODUCTS_TABLE_SQL`, `_PRODUCT_COLUMNS`, and `select_exprs`
- [ ] 1.6 Verify fresh DB init (via `_SCHEMA_SQL`) and existing-DB startup (via rebuild) both yield a `weight_grams` column defaulting to 300; re-running init is a no-op (guard short-circuits)

## 2. Models (`app/models/products.py`)

- [ ] 2.1 Add local constant `MAX_WEIGHT_GRAMS = 100_000` (mirrors the module's local `MAX_STOCK`, not the `constants.py` one)
- [ ] 2.2 Add `weight_grams: int = Field(default=300, ge=1, le=MAX_WEIGHT_GRAMS)` to `CreateProductRequest`
- [ ] 2.3 Add `weight_grams: int | None = Field(default=None, ge=1, le=MAX_WEIGHT_GRAMS)` to `UpdateProductRequest`
- [ ] 2.4 Add `weight_grams: int` to `ProductAdminResponse`
- [ ] 2.5 Confirm public `ProductResponse` does NOT include `weight_grams` (Pydantic ignores the extra row key on construction — verify no `extra="forbid"` config)

## 3. Service (`app/services/product_service.py`)

- [ ] 3.1 `create_product`: add `"weight_grams"` to the explicit `columns` list and `data.get("weight_grams", 300)` to `values`, at matching positions
- [ ] 3.2 `upsert_product` + `update_product`: add `"weight_grams": data.get("weight_grams")` to each `field_map` (non-None → persisted)
- [ ] 3.3 Confirm `materials`, `days_to_craft`, `is_active`, `is_featured` are ALREADY in the `field_map`s (no service change needed for those — they're only dropped by the CSV parser)
- [ ] 3.4 `weight_grams` flows into `ProductAdminResponse` via the existing `SELECT *` → `_row_to_dict` mapping

## 4. CSV import (`app/routes/admin.py`) — parser-only except weight_grams touches the service too

- [ ] 4.1 Add a case-insensitive boolean parse helper (`true/false/1/0/yes/no`; else per-row error)
- [ ] 4.2 Parse optional `weight_grams` column (int, range 1–`MAX_WEIGHT_GRAMS`, per-row error on invalid); add to `data` when present. Missing → DB `DEFAULT 300` for new rows; existing rows keep current weight
- [ ] 4.3 Parse optional `is_active` column (bool helper); add to `data` when present
- [ ] 4.4 Parse optional `is_featured` column (bool helper); add to `data` when present
- [ ] 4.5 Parse optional `materials` (string) and `days_to_craft` (int, validated like `stock`); add to `data` when present
- [ ] 4.6 Update the import docstring/summary and the sample CSV shown in the products page UI

## 5. Frontend — form (`frontend/components/admin/ProductForm.tsx`)

- [ ] 5.1 Add `weight_grams` to `ProductFormData` and initialize (default 300 on create, product value on edit)
- [ ] 5.2 Add a grams number input with validation (integer ≥ 0)
- [ ] 5.3 Add an `is_active` toggle bound to `formData.is_active`, included in the submit payload
- [ ] 5.4 Add i18n labels to `frontend/messages/en.json` and `bg.json` (weight, isActive, help text)

## 6. Frontend — types & mock (`frontend/lib`)

- [ ] 6.1 Add `weight_grams` to the admin product interface in `lib/types.ts`
- [ ] 6.2 Update `lib/mock-api.ts` product fixtures + create/update handlers to carry `weight_grams` and `is_active`

## 7. Cross-spec bookkeeping

- [ ] 7.1 Annotate `openspec/changes/shipping-pricing` (proposal + design) that the `weight_grams` data half is delivered by `product-mgmt-completeness`; shipping-pricing only consumes it

## 8. Tests

- [ ] 8.1 Model tests: create defaults `weight_grams` to 300; explicit value persists; update changes it
- [ ] 8.2 Admin route test: create/update round-trip includes `weight_grams`; public product endpoint omits it
- [ ] 8.3 CSV import tests: extended columns applied; missing `weight_grams` → 300; invalid weight/bool → row error and skipped
- [ ] 8.4 Frontend test: form renders weight input + is_active toggle and submits them

## 9. Verify

- [ ] 9.1 Run `make test-backend` and `make test-frontend`; `make lint`
- [ ] 9.2 Manual smoke: create a product with weight via form, edit it inactive, import a CSV with weight column
