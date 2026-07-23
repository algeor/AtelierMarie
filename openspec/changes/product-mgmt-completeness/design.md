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
Adopt Decision 13's column definition verbatim. 300g is a safe middle for candles (range ~150–800g); courier APIs tolerate ±200g, so imprecise defaults are acceptable and refineable. `NOT NULL DEFAULT` means existing rows backfill to 300 automatically — no data migration needed beyond the column add.

**Alternative considered:** nullable weight with runtime fallback. Rejected — pushes the default into every read site and complicates the shipping calc later.

### 2. Exclude `weight_grams` from public `ProductResponse` (deviation from Decision 13)
Decision 13 listed `ProductResponse.weight_grams`. We deviate: weight is a shipping *input* the customer chose not to see (explicit product decision). The shipping calculator reads weight server-side directly from `products`, so it never needs the value in the public JSON. Keeping it out avoids leaking a logistics detail and keeps the public contract minimal.

**Trade-off:** if a future feature wants to show weight to customers, add it to `ProductResponse` then — cheap and non-breaking.

### 3. Schema change lives in both `products` and `products_new`
`app/database.py` maintains a `products_new` table used by the column-rebuild migration path. Add `weight_grams` to both the live `CREATE TABLE products` and `products_new`, and include it in the migration's column-copy list so a rebuild preserves it.

### 4. CSV import: additive, default-preserving parsing
Extend the import row parser to read the optional columns only when present in the header, mirroring the existing pattern for `category`/`image_url`. Absent column → field omitted from the payload → model default applies (`weight_grams`=300, `is_active`=true, `is_featured`=false). Booleans parse case-insensitively (`true/false/1/0/yes/no`); invalid values become a per-row error (skipped row), consistent with existing stock validation.

### 5. `is_active` in the form is just another field
The `UpdateProductRequest`/`CreateProductRequest` already accept `is_active`. The form adds a toggle bound to `formData.is_active` and includes it in the submit payload. No API change. The list-table toggle stays as a convenience shortcut.

## Risks / Trade-offs

- **CSV boolean ambiguity** → define an explicit accepted-values set and reject others as a row error, so a typo can't silently deactivate a product.
- **Migration double-definition drift** (forgetting `products_new`) → checklist item in tasks; a rebuild would otherwise drop the column.
- **Spec conflict with `shipping-pricing`** (both claiming `weight_grams`) → annotate `shipping-pricing` that the data half moved here; it only consumes the field.
- **Weight defaults are approximate** → acceptable per Decision 13; admin can refine per product over time.

## Migration Plan

1. Add column to `products` + `products_new` + migration copy list. Existing rows backfill to 300 via the `DEFAULT`.
2. Ship model + service + CSV + form together (single change).
3. Rollback: the column is additive and nullable-by-default-value; reverting code leaves a harmless unused column. No destructive migration.

## Open Questions

- None blocking. (Whether to later surface weight to customers is deferred, not part of this change.)
