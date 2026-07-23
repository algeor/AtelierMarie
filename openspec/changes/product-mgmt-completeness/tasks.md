## 1. Database schema (`app/database.py`)

- [ ] 1.1 Add `weight_grams INTEGER NOT NULL DEFAULT 300` to the `CREATE TABLE products` statement
- [ ] 1.2 Add `weight_grams INTEGER NOT NULL DEFAULT 300` to the `products_new` migration table
- [ ] 1.3 Add `weight_grams` to the migration column-copy list so a table rebuild preserves it (default 300 for legacy rows)
- [ ] 1.4 Verify a fresh DB init and an existing-DB startup both produce a `weight_grams` column defaulting to 300

## 2. Models (`app/models/products.py`)

- [ ] 2.1 Add `weight_grams: int = Field(default=300, ge=0, le=<sane max>)` to `CreateProductRequest`
- [ ] 2.2 Add `weight_grams: int | None = Field(default=None, ge=0, le=<sane max>)` to `UpdateProductRequest`
- [ ] 2.3 Add `weight_grams: int` to `ProductAdminResponse`
- [ ] 2.4 Confirm public `ProductResponse` does NOT include `weight_grams` (intentional exclusion)

## 3. Service (`app/services/product_service.py`)

- [ ] 3.1 Include `weight_grams` in the product INSERT column list + values
- [ ] 3.2 Include `weight_grams` in the partial UPDATE column handling
- [ ] 3.3 Ensure `weight_grams` is selected/mapped into the admin response

## 4. CSV import (`app/routes/admin.py`)

- [ ] 4.1 Parse optional `weight_grams` column (int, default 300 when absent; per-row error on invalid)
- [ ] 4.2 Parse optional `is_active` column (bool: true/false/1/0/yes/no, default true; per-row error on invalid)
- [ ] 4.3 Parse optional `is_featured` column (bool, default false)
- [ ] 4.4 Parse optional `materials` column (string, optional)
- [ ] 4.5 Parse optional `days_to_craft` column (int, optional; per-row error on invalid)
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
