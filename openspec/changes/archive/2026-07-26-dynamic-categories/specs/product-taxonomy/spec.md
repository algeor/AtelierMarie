## ADDED Requirements

### Requirement: Product taxonomy is managed data
The system SHALL persist product taxonomy as admin-managed product types, categories/tiers, and labels. Each taxonomy term SHALL use an immutable slug, bilingual names (`name_en` required, `name_bg` optional), `sort_order`, `is_active`, and timestamps. Products SHALL reference one product type, optionally one category/tier, and zero or more labels.

#### Scenario: Product type persisted dynamically
- **WHEN** an admin creates product type "Boxes"
- **THEN** a product type row exists with `slug` = "boxes", `name_en` = "Boxes", and `is_active` = 1
- **AND** the value is available through taxonomy APIs without a code change

#### Scenario: Category tier persisted dynamically
- **WHEN** an admin creates category/tier "Premium"
- **THEN** a category row exists with `slug` = "premium", `name_en` = "Premium", and `is_active` = 1
- **AND** product forms can use it without a hardcoded frontend constant

#### Scenario: Label persisted dynamically
- **WHEN** an admin creates label "Winter"
- **THEN** a label row exists with `slug` = "winter", `name_en` = "Winter", and `is_active` = 1
- **AND** products can be assigned that label without a deploy

#### Scenario: Product has multiple taxonomy facets
- **WHEN** a product is assigned product type "candles", category "medium", and labels "winter" and "gift"
- **THEN** the product stores `product_type_slug` = "candles", `category_slug` = "medium", and two product-label assignments

### Requirement: Taxonomy values are not hardcoded in the frontend
The system SHALL source product types, categories/tiers, and labels from taxonomy APIs for admin product forms, admin taxonomy management views, and storefront filters. The frontend SHALL NOT define hardcoded lists of product types, categories/tiers, or labels for production behavior.

#### Scenario: Product form options come from API
- **WHEN** the admin product form renders
- **THEN** product type, category/tier, and label options are fetched from admin taxonomy APIs
- **AND** no hardcoded product type/category/label constants are used to define assignable options

#### Scenario: Storefront filter options come from API
- **WHEN** the product listing page renders
- **THEN** sidebar filter groups are built from the public taxonomy endpoint
- **AND** labels such as "Winter" or product types such as "Boxes" appear after admin creation without a code change

### Requirement: Existing category values migrate to taxonomy labels
On migration the system SHALL convert distinct non-null legacy `products.category` values into managed labels, assign those labels to matching products, default existing products to product type `candles`, ensure seed product types/categories/labels exist, and record each original-value-to-label mapping. The migration SHALL be idempotent and marker-guarded so pre-existing seed taxonomy rows cannot cause product-label backfill to be skipped.

#### Scenario: Legacy fragrance category becomes label
- **WHEN** products contain legacy category "Floral" before migration
- **THEN** label "floral" exists afterward
- **AND** those products have a product-label assignment for "floral"
- **AND** the migration mapping records "Floral" -> "floral"

#### Scenario: Existing products default to candles
- **WHEN** products exist before taxonomy migration
- **THEN** each product with no product type is assigned `product_type_slug` = "candles"

#### Scenario: Category tier remains unset by migration
- **WHEN** products contain legacy fragrance values such as "Floral" or "Woody"
- **THEN** those values are not stored as size/tier categories
- **AND** `category_slug` remains NULL until an admin assigns small/medium/premium or another category/tier

#### Scenario: Migration runs once
- **WHEN** the app starts again after `product_taxonomy_v1` already ran
- **THEN** seed/backfill does not duplicate taxonomy terms or assignments

#### Scenario: Slug collision suffixed
- **WHEN** two distinct legacy values slugify to the same label slug
- **THEN** the second is suffixed (for example `-2`) so slugs remain unique
- **AND** products are updated according to the recorded exact original-value mapping

### Requirement: Public taxonomy endpoint
The system SHALL expose `GET /v1/taxonomy` returning active product types, categories/tiers, and labels ordered by `sort_order`, localized by optional `locale` query parameter (`en`|`bg`, default `en`) with fallback to `name_en` when `name_bg` is NULL.

#### Scenario: List active taxonomy in English
- **WHEN** `GET /v1/taxonomy` is called
- **THEN** the response contains active product types, categories, and labels with `slug` and localized `name`, ordered by `sort_order`

#### Scenario: List taxonomy in Bulgarian with fallback
- **WHEN** `GET /v1/taxonomy?locale=bg` is called and a term has NULL `name_bg`
- **THEN** that term's `name` falls back to `name_en`

#### Scenario: Inactive taxonomy excluded from public endpoint
- **WHEN** a taxonomy term has `is_active` = 0
- **THEN** it is not returned by the public taxonomy endpoint
- **AND** products that reference that term still resolve display names through product response metadata

### Requirement: Admin taxonomy CRUD
The system SHALL expose dedicated admin endpoints and views for creating, listing, updating, activating/deactivating, reordering, and deleting product types, categories/tiers, and labels. These endpoints SHALL be protected by admin auth. List responses SHALL include inactive terms and each term's in-use product count.

#### Scenario: Create product type from dedicated admin view
- **WHEN** an admin creates product type "Boxes" in the taxonomy management view
- **THEN** it appears in the admin product form and storefront filter menu without a code change

#### Scenario: Create label from dedicated admin view
- **WHEN** an admin creates label "Winter" in the taxonomy management view
- **THEN** it appears as an assignable product label and public filter option while active

#### Scenario: Rename term without orphaning products
- **WHEN** an admin renames category/tier "Medium" to "Standard"
- **THEN** the slug is unchanged
- **AND** products referencing the slug are unaffected

#### Scenario: Slug is immutable
- **WHEN** an admin update request includes a different slug for an existing taxonomy term
- **THEN** the request is rejected or the slug field is ignored according to the request schema
- **AND** products continue referencing the original slug

#### Scenario: Non-admin cannot manage taxonomy
- **WHEN** a non-admin calls any `/v1/admin/taxonomy/*` endpoint
- **THEN** the request is rejected with 401/403

### Requirement: Taxonomy delete is guarded; deactivate hides without deleting
The system SHALL block hard deletion of a taxonomy term while any product references it, returning 409 with guidance to reassign or deactivate. Deactivating a term SHALL hide it from public filters and new-assignment controls while leaving referencing products intact.

#### Scenario: Delete product type blocked while in use
- **WHEN** an admin DELETEs product type "candles" while products reference it
- **THEN** the response is 409 and the product type is not deleted

#### Scenario: Delete label blocked while in use
- **WHEN** an admin DELETEs label "winter" while products reference it
- **THEN** the response is 409 and the label is not deleted

#### Scenario: Delete allowed when unused
- **WHEN** an admin DELETEs an unused taxonomy term
- **THEN** the term is removed

#### Scenario: Deactivate retires term in use
- **WHEN** an admin sets `is_active` = 0 on a label referenced by products
- **THEN** the label disappears from new-assignment controls and public filter menus
- **AND** products keep the assignment and still display the label name
