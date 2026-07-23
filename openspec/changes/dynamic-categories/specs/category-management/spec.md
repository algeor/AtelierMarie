## ADDED Requirements

### Requirement: Categories are managed data
The system SHALL persist categories in a `categories` table keyed by a stable `slug`, with bilingual names (`name_en` required, `name_bg` optional), `sort_order`, `is_active`, and timestamps. Products SHALL reference a category by its slug via the existing `products.category` column.

#### Scenario: Category persisted with slug and names
- **WHEN** a category "Floral" is created
- **THEN** a row exists with `slug` = "floral", `name_en` = "Floral", and `is_active` = 1

#### Scenario: Product references category by slug
- **WHEN** a product is assigned category "floral"
- **THEN** `products.category` stores the slug "floral"

### Requirement: Existing category values are migrated to managed categories
On migration the system SHALL seed the `categories` table from the distinct non-null `products.category` values, create a category per value (`slug` = slugified value, `name_en` = original value), ensure the six default fragrance families exist, and rewrite `products.category` to slugs. The migration SHALL be idempotent.

#### Scenario: Distinct values seeded
- **WHEN** products contain categories "Floral" and "Woody" before migration
- **THEN** categories "floral" and "woody" exist afterward and those products reference the slugs

#### Scenario: Migration runs once
- **WHEN** the app starts again after migration already ran
- **THEN** the seed/backfill does not duplicate categories or alter products

#### Scenario: Slug collision suffixed
- **WHEN** two distinct display values slugify to the same slug
- **THEN** the second is suffixed (e.g. `-2`) so slugs remain unique

### Requirement: Public categories endpoint
The system SHALL expose `GET /v1/categories` returning active categories ordered by `sort_order`, localized by an optional `locale` query parameter (`en`|`bg`, default `en`) with fallback to `name_en` when `name_bg` is NULL.

#### Scenario: List active categories in English
- **WHEN** `GET /v1/categories` is called
- **THEN** the response contains active categories with `slug` and localized `name`, ordered by `sort_order`

#### Scenario: List categories in Bulgarian with fallback
- **WHEN** `GET /v1/categories?locale=bg` is called and a category has NULL `name_bg`
- **THEN** that category's `name` falls back to `name_en`

#### Scenario: Inactive categories excluded
- **WHEN** a category has `is_active` = 0
- **THEN** it is not returned by the public endpoint

### Requirement: Admin category CRUD
The system SHALL expose admin endpoints to create, list, update, and delete categories under `/v1/admin/categories`, protected by admin auth. Update SHALL support renaming (`name_en`/`name_bg`), reordering (`sort_order`), and toggling `is_active`. List SHALL include inactive categories and each category's in-use product count.

#### Scenario: Create a category
- **WHEN** an admin POSTs a new category with `name_en` = "Herbal"
- **THEN** it is created with `slug` = "herbal" and appears in the admin list

#### Scenario: Rename a category without orphaning products
- **WHEN** an admin PATCHes `name_en` of an existing category
- **THEN** the slug is unchanged and products referencing it are unaffected

#### Scenario: Non-admin cannot manage categories
- **WHEN** a non-admin calls any `/v1/admin/categories` endpoint
- **THEN** the request is rejected with 401/403

### Requirement: Category delete is guarded; deactivate hides without deleting
The system SHALL block hard deletion of a category while any product references its slug, returning 409 with guidance to reassign or deactivate. Deactivating a category (`is_active` = 0) SHALL hide it from the public endpoint and admin form pickers while leaving referencing products intact.

#### Scenario: Delete blocked while in use
- **WHEN** an admin DELETEs a category that 3 products reference
- **THEN** the response is 409 and the category is not deleted

#### Scenario: Delete allowed when unused
- **WHEN** an admin DELETEs a category referenced by no products
- **THEN** the category is removed

#### Scenario: Deactivate retires a category in use
- **WHEN** an admin sets `is_active` = 0 on a category referenced by products
- **THEN** the category disappears from pickers and the public list, but the products keep their slug and still display the category name
