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

**Alternative (simpler MVP):** single-language `name` only, no localization of category display. Rejected as inconsistent with the codebase's bilingual contract — but it remains the natural fallback if migration/localization effort needs trimming in a future rescope.

### 3. Migration: map existing values to unique slugs, seed defaults, backfill products
On startup migration:
1. Create `categories`, `category_slug_migrations`, and a lightweight `schema_migrations` marker table if missing.
2. If `schema_migrations` already contains `dynamic_categories_v1`, skip the category backfill. Do not guard on `categories` being non-empty, because defaults may exist before product values are migrated.
3. Read `SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND TRIM(category) != ''` before rewriting products.
4. For each distinct original value, deterministically assign a unique slug (`slugify(value)`, suffixing `-2`, `-3`, etc. on collision) and store `(original_value, slug)` in `category_slug_migrations`.
5. Insert categories from that mapping with `name_en = original_value`, plus the six default fragrance families (insert if absent).
6. Backfill products by mapping exact original values to assigned slugs (`UPDATE products SET category = ? WHERE category = ?` per mapping entry), then write the `dynamic_categories_v1` marker in the same transaction.

This makes collision handling reversible and prevents a lossy `UPDATE products SET category = slugify(category)` rewrite where two legacy values could collapse to one slug. Original values are recoverable from `category_slug_migrations` and `categories.name_en`.

### 4. Product responses carry display labels; `products.category` remains the filtering slug
Public `ProductResponse` adds `category_name: string | null`. `category` remains the stored slug used for filtering and URLs/query parameters; `category_name` is resolved in the product service using the requested locale:
- `locale=en` → `categories.name_en`
- `locale=bg` → `COALESCE(categories.name_bg, categories.name_en)`
- missing category row → fallback to the raw slug for compatibility, but this should only happen if data was corrupted outside the delete guard

The product list, search, and detail queries should resolve labels with a `LEFT JOIN categories` or an equivalent batched lookup, not a per-product category query. The join must include inactive categories so retired categories still display correctly on products that reference them. `GET /v1/categories` remains active-only and is not the source of truth for rendering product-assigned inactive categories.

### 5. `products.category` stays a soft reference (validated, not FK-enforced)
Create validates `category` is an existing **active** slug and rejects unknown or inactive slugs (422). Update validates only actual category reassignment: omitted category values leave the current slug untouched, and sending the product's existing inactive slug is accepted so admins can edit other fields on products assigned to retired categories. Assigning a different inactive slug is rejected.

CSV import follows the same assignment rule as product create/update: category values must be existing active slugs; the importer reports row-level validation errors and does not auto-create categories.

We do NOT add a hard SQL foreign key: it complicates the migration ordering and the delete story, and the validation plus delete guard are sufficient for this SQLite app. FTS continues to index `products.category` (now a slug) — acceptable; category search by display name is out of scope for this change.

### 6. Delete vs deactivate
- **Deactivate** (`is_active = 0`): hides the category from new-assignment pickers and the public category endpoint; existing products keep their slug and still display (name resolved from the row, which still exists). Primary "retire a category" path.
- **Hard delete**: allowed only when no product references the slug; otherwise 409 with a message to reassign or deactivate. Prevents dangling slugs on products.

### 7. Endpoints
- `GET /v1/categories` (public): active categories, localized by `?locale=`, ordered by `sort_order`.
- `GET /v1/admin/categories`, `POST`, `PATCH /{slug}`, `DELETE /{slug}` (admin): full management.

### 8. Storefront pills derive from products, names come from product metadata
The filter pills currently derive from product data. They continue to derive the unique category slugs from the product list so empty categories stay hidden and "All" stays first. Labels come from each product's `category_name`; if multiple products with the same slug are present, the first non-empty label for that slug is used. Filtering stays keyed by slug.

This avoids a second active-category fetch and handles inactive categories referenced by visible products, because product responses resolve labels from all non-deleted category rows.

### 9. Admin forms use admin category data
The product create/edit form fetches admin categories, not only the active public list. Create mode presents active categories. Edit mode includes the product's current category even when inactive, marked as retired; the admin can keep that current inactive category while editing other fields, but cannot assign an inactive category to another product. New assignment choices are active categories only.

## Risks / Trade-offs

- **Data migration rewrites `products.category`** → make it marker-guarded and mapping-based; preserve original text in `category_slug_migrations` and `name_en`; document restore SQL for rollback.
- **Slug collisions** (two display values slugify to the same slug) → assign deterministic suffixes (`-2`, `-3`) from the migration mapping; log collisions with original values.
- **FTS indexes slugs now, not display names** → minor; category was a weak search signal. If needed later, index the localized name instead.
- **Three changes (A, B, C) touch `admin-products` form** → C adds the dropdown-source requirement as a separate ADDED requirement to avoid clashing with A's and B's form deltas.
- **Orphan slug if a product references a deleted category** → prevented by the delete-guard (409 when in use).
- **Inactive category disappears from active category list** → product responses resolve `category_name` independently of `GET /v1/categories`, and admin edit forms use the admin category list.

## Migration Plan

1. Ship table + migration + seed + backfill together with the endpoints and UI.
2. Migration runs once on startup inside one transaction, guarded by the `dynamic_categories_v1` marker. Existing rows get mapped slugs; six defaults are ensured.
3. Rollback: do not assume a code-only revert restores display names, because product rows now contain slugs. If rollback is required, restore product categories from `category_slug_migrations` before reverting the code path that understands category slugs. The `categories` table can remain harmlessly, but the product data restoration is the compatibility step.

## Open Questions

None. CSV import validates against existing active slugs like the form; auto-create is out of scope.
