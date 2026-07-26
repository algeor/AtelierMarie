## Context

The original dynamic-categories design promoted `products.category` from free text to a managed flat category. The desired shop model is broader:

```
Product type       candles, boxes, future product families
Category/tier      small, medium, premium, future admin-defined groups
Labels             winter, gift, floral, woody, Christmas, wedding, relaxing
```

These are independent facets. A candle can be medium and tagged winter/gift/floral. A box can be premium and tagged gift/wedding. A future product family can reuse the same category/tier terms and labels without code changes.

The admin must be able to create product types, categories/tiers, and labels dynamically in dedicated views. Hardcoded frontend constants for taxonomy values are out of scope and should be removed.

## Goals / Non-Goals

**Goals:**
- Managed product taxonomy that supports candles first, boxes next, and future product types.
- Dedicated admin views for product types, categories/tiers, and labels.
- Sidebar faceted storefront filtering by product type, category/tier, labels, stock, search, and sort.
- Safe migration from existing free-text `products.category` values.
- Localized taxonomy display names for English and Bulgarian storefronts.

**Non-Goals:**
- Nested category trees.
- Per-category landing pages, SEO copy, imagery, or merchandising rules.
- Variant/SKU modeling for size/price differences inside one product.
- Hard SQL foreign keys for all taxonomy assignments; validation and delete guards are sufficient for this SQLite app.

## Decisions

### 1. Taxonomy is split by role, not stored in one flat category list

Use separate managed entities so UI and data stay understandable:

```
product_types(
  slug        TEXT PRIMARY KEY,
  name_en     TEXT NOT NULL,
  name_bg     TEXT,
  sort_order  INTEGER NOT NULL DEFAULT 0,
  is_active   INTEGER NOT NULL DEFAULT 1,
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
)

product_categories(
  slug        TEXT PRIMARY KEY,
  name_en     TEXT NOT NULL,
  name_bg     TEXT,
  sort_order  INTEGER NOT NULL DEFAULT 0,
  is_active   INTEGER NOT NULL DEFAULT 1,
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
)

product_labels(
  slug        TEXT PRIMARY KEY,
  name_en     TEXT NOT NULL,
  name_bg     TEXT,
  sort_order  INTEGER NOT NULL DEFAULT 0,
  is_active   INTEGER NOT NULL DEFAULT 1,
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
)

product_label_assignments(
  product_id  TEXT NOT NULL,
  label_slug  TEXT NOT NULL,
  PRIMARY KEY(product_id, label_slug)
)
```

`products` gains:

```
product_type_slug TEXT NOT NULL DEFAULT 'candles'
category_slug     TEXT
```

The existing `products.category` column remains during migration compatibility but is no longer the primary taxonomy model. It can be kept as a legacy column or later renamed/dropped through a separate migration if needed.

### 2. Slugs are stable keys; names are display data

All taxonomy terms use immutable slugs. Renaming a product type, category/tier, or label changes `name_en`/`name_bg` only. Product rows and assignments keep referencing slugs.

Slug creation is server-side from `name_en`, using lowercase hyphenated ASCII. Collisions get deterministic suffixes (`-2`, `-3`).

### 3. Admin-managed means no hardcoded taxonomy values

Seed values are only startup data so a fresh shop is usable. They do not replace admin management and must not be duplicated as frontend constants.

Initial seed values:

- Product types: `candles`, `boxes`
- Categories/tiers: `small`, `medium`, `premium`
- Labels: current fragrance families (`floral`, `woody`, `fresh`, `gourmand`, `spicy`, `citrus`) plus useful starter labels such as `winter`, `gift`, `christmas`

The admin can create, rename, reorder, deactivate, and delete unused values from dedicated taxonomy views.

### 4. Migration maps legacy `products.category` values to labels

The current `products.category` values are fragrance-family-like labels, not product types or size/tier categories. Migration should preserve them as labels.

On startup migration:

1. Create taxonomy tables, assignment table, mapping table, and a lightweight `schema_migrations` marker if missing.
2. Add `product_type_slug` and `category_slug` to `products` if missing.
3. Ensure seed taxonomy terms exist.
4. If marker `product_taxonomy_v1` exists, skip assignment backfill.
5. Read distinct non-null `products.category` values before any rewrite.
6. For each original value, create or reuse a label slug, record `(original_value, label_slug)` in a migration mapping table, and assign that label to products with the exact original value.
7. Set existing products to `product_type_slug = 'candles'` when unset.
8. Leave `category_slug` NULL; admins can assign small/medium/premium later.
9. Write the migration marker in the same transaction.

This avoids pretending `Floral` is a size/tier category and preserves existing storefront grouping as labels.

### 5. Product responses carry taxonomy display metadata

Public product responses keep slug fields for filtering and include localized display metadata:

```
product_type: string
product_type_name: string
category: string | null
category_name: string | null
labels: [{ slug: string, name: string }]
```

For backward compatibility, `category` in public responses maps to `category_slug` after this change, not the old legacy category text. The product labels carry legacy fragrance families and purpose/season values.

Display names resolve by locale:

- `locale=en` uses `name_en`
- `locale=bg` uses `COALESCE(name_bg, name_en)`
- missing taxonomy row falls back to the raw slug for compatibility

Resolution must include inactive taxonomy terms when rendering products that already reference them, so retired labels still display on existing products.

### 6. Assignment validation uses active terms, with preserve-current exceptions

Product create validates:

- supplied `product_type` is an existing active product type
- supplied `category` is NULL or an existing active category/tier
- supplied labels are existing active label slugs

Product update validates only actual reassignment. Omitted values preserve existing assignments. Sending the current inactive product type/category/label is allowed so admins can edit unrelated fields without being forced to reclassify immediately. Assigning a different inactive term is rejected.

CSV import follows the same rule and reports row-level errors. It does not auto-create product types, categories, or labels.

### 7. Delete vs deactivate

Deactivate hides a term from new-assignment controls and public filter menus, but existing products keep displaying the term.

Hard delete is blocked with 409 while any product references the term:

- product type referenced by `products.product_type_slug`
- category referenced by `products.category_slug`
- label referenced by `product_label_assignments.label_slug`

Unused terms may be deleted.

### 8. Public taxonomy and product endpoints

Public endpoint:

- `GET /v1/taxonomy?locale=en|bg` returns active product types, categories, and labels ordered by `sort_order`.

Admin endpoints:

- `GET/POST /v1/admin/taxonomy/product-types`
- `PATCH/DELETE /v1/admin/taxonomy/product-types/{slug}`
- `GET/POST /v1/admin/taxonomy/categories`
- `PATCH/DELETE /v1/admin/taxonomy/categories/{slug}`
- `GET/POST /v1/admin/taxonomy/labels`
- `PATCH/DELETE /v1/admin/taxonomy/labels/{slug}`

Product listing filters:

- `product_type=<slug>`
- `category=<slug>`
- `labels=<slug>,<slug>` or repeated `label=<slug>` parameters
- existing `q`, `sort`, `in_stock`, `page`, `limit`, `locale`

Multiple labels use AND semantics by default: a product must have every selected label. This is more useful for purpose filters like `winter` + `gift`. If OR behavior is desired later, add an explicit `label_mode=any` parameter.

### 9. Storefront sidebar derives controls from taxonomy and counts from products

The product listing page fetches products and taxonomy data. The sidebar shows grouped filters:

```
Product Type
  Candles
  Boxes

Category
  Small
  Medium
  Premium

Labels
  Winter
  Gift
  Floral
  Woody
```

Desktop uses a left sidebar. Mobile uses a collapsible filter panel. Selected filters are shown as removable chips above the grid. The grid updates without a full page reload.

Filter option labels come from taxonomy APIs. Product cards and detail pages use product response metadata. The UI must not contain hardcoded taxonomy lists.

### 10. Admin product forms use taxonomy APIs

Create/edit product forms fetch admin taxonomy data:

- product type: required dropdown, active options in create mode
- category/tier: optional dropdown, active options in create mode
- labels: multi-select control with active labels

Edit mode includes the product's current inactive terms marked as retired so they can be preserved while editing unrelated fields.

## Risks / Trade-offs

- **Wider scope than flat categories**: this touches schema, APIs, admin UI, storefront UI, and migration. The benefit is a taxonomy model that fits candles, boxes, sizes/tiers, and labels without rework.
- **Legacy `products.category` meaning changes**: existing values become labels, not category/tier. This matches the actual data better but requires API/frontend updates.
- **Facet filtering can become complex**: start with product type, category, and labels. Hierarchies and merchandising pages stay out of scope.
- **Inactive terms in product display**: product rendering must resolve labels independently of active-only public taxonomy filters.

## Migration Plan

1. Ship taxonomy tables, migration, seed data, endpoints, and UI together.
2. Migration runs once on startup inside one transaction, guarded by `product_taxonomy_v1`.
3. Existing products become `candles`; existing category text becomes labels and label assignments.
4. Rollback: restore behavior from the legacy `products.category` values only if the old code path is restored. The taxonomy tables can remain harmlessly, but product listing code must understand which taxonomy model is active.

## Open Questions

None for now. The admin will manage product types, category/tier terms, and labels dynamically; no hardcoded taxonomy lists should remain in the frontend.
