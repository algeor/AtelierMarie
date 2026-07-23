## Context

Category handling is split across two surfaces with different levels of "managed":

```
Storefront filter pills   → ALREADY dynamic (ProductListingClient derives unique
                            non-null product.category values; pills built from data)
Product detail badge      → shows raw product.category string
Admin form dropdown       → HARDCODED const CATEGORIES = [6 fragrance families]
Backend                   → products.category is a free-text TEXT column;
                            filter is exact-match; FTS indexes category text
```

So the pain is the hardcoded admin dropdown and the lack of any place to manage the list. The backend has no category entity — just a string column.

## Goals / Non-Goals

**Goals:**
- A managed `categories` entity the shop owner can CRUD without a deploy.
- Admin form dropdown and storefront names sourced from managed data.
- Safe migration of existing category values with no orphaned products.

**Non-Goals:**
- Category hierarchy / nesting (flat list only).
- Multi-category products (a product still has at most one category).
- Per-category imagery, SEO pages, or merchandising rules.

## Decisions

### 1. `categories` table, slug as the stable key
```
categories(
  slug        TEXT PRIMARY KEY,        -- stable identifier, stored on products
  name_en     TEXT NOT NULL,
  name_bg     TEXT,                    -- nullable; falls back to name_en
  sort_order  INTEGER NOT NULL DEFAULT 0,
  is_active   INTEGER NOT NULL DEFAULT 1,
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
)
```
`products.category` (existing TEXT column) now stores a category **slug**. Using a stable slug (not the display name) means renaming a category doesn't orphan products.

### 2. Bilingual categories (key decision)
Categories are bilingual (`name_en` / `name_bg`) to match the rest of the app (bilingual product content, per-locale FTS, locale routing). The storefront resolves slug → localized name with fallback to `name_en`.

**Alternative (simpler MVP):** single-language `name` only, no localization of category display. Rejected as inconsistent with the codebase's bilingual contract — but it's the natural fallback if migration/localization effort needs trimming. Flagged in Open Questions.

### 3. Migration: slugify existing values, seed defaults, backfill products
On startup migration:
1. Create `categories` table.
2. Read `SELECT DISTINCT category FROM products WHERE category IS NOT NULL`.
3. For each distinct value, insert a category with `slug = slugify(value)`, `name_en = value`.
4. Ensure the six default fragrance families exist (insert if absent).
5. `UPDATE products SET category = slugify(category)` so products reference slugs.

Idempotent (guarded by "table already populated" check) so it runs once. Original values are recoverable from `name_en`.

### 4. `products.category` stays a soft reference (validated, not FK-enforced)
Create/update validate `category` is an existing **active** slug and reject otherwise (422). We do NOT add a hard SQL foreign key: it complicates the migration ordering and the delete story, and the validation layer is sufficient. FTS continues to index `products.category` (now a slug) — acceptable; category search was a minor FTS signal.

### 5. Delete vs deactivate
- **Deactivate** (`is_active = 0`): hides the category from the form dropdown and storefront pickers; existing products keep their slug and still display (name resolved from the row, which still exists). Primary "retire a category" path.
- **Hard delete**: allowed only when no product references the slug; otherwise 409 with a message to reassign or deactivate. Prevents dangling slugs on products.

### 6. Endpoints
- `GET /v1/categories` (public): active categories, localized by `?locale=`, ordered by `sort_order`.
- `GET /v1/admin/categories`, `POST`, `PATCH /{slug}`, `DELETE /{slug}` (admin): full management.

### 7. Storefront pills sourced from categories, names localized
The filter pills currently derive from product data. They continue to work, but category **names** are resolved to the current locale via the categories list (slug → localized name). Pills for slugs present on products are shown; "All" stays first. This keeps the existing "hide pills for empty categories" behavior.

## Risks / Trade-offs

- **Data migration rewrites `products.category`** → make it idempotent and guarded; preserve original text in `name_en`; document rollback (revert code; slugs remain but render fine).
- **Slug collisions** (two display values slugify to the same slug) → on seed, detect collision and suffix (`-2`); log it.
- **FTS indexes slugs now, not display names** → minor; category was a weak search signal. If needed later, index the localized name instead.
- **Three changes (A, B, C) touch `admin-products` form** → C adds the dropdown-source requirement as a separate ADDED requirement to avoid clashing with A's and B's form deltas.
- **Orphan slug if a product references a deleted category** → prevented by the delete-guard (409 when in use).

## Migration Plan

1. Ship table + migration + seed + backfill together with the endpoints and UI.
2. Migration runs once on startup (guarded). Existing rows get slugs; six defaults ensured.
3. Rollback: revert code. The `categories` table and slug values remain but are harmless; the old frontend const still matches the six default slugs' display names. No destructive step.

## Open Questions

- **Bilingual vs single-language category names** (Decision 2) — proceeding bilingual for consistency; simpler single-language is the fallback if scope needs trimming.
- Should CSV import validate/create categories on the fly? Proposed: validate against existing slugs like the form; auto-create is out of scope.
