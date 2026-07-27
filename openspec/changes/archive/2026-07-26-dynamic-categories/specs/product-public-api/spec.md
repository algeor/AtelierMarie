## MODIFIED Requirements

### Requirement: Product responses expose managed taxonomy display metadata
Public product list and detail responses SHALL expose taxonomy slugs used for filtering and localized display names resolved from managed taxonomy data. Responses SHALL include product type, optional category/tier, and labels. Display lookup SHALL include inactive referenced terms so retired taxonomy still renders correctly on products. If a taxonomy row is missing, display names SHALL fall back to the raw slug for compatibility.

#### Scenario: List response includes localized taxonomy names
- **WHEN** `GET /v1/products?locale=bg` returns a product with `product_type` = "candles", `category` = "medium", and label "winter"
- **THEN** that product includes those slugs
- **AND** includes Bulgarian display names when present, otherwise English fallback names

#### Scenario: Detail response includes inactive taxonomy names
- **WHEN** `GET /v1/products/{id}?locale=en` returns a product assigned to an inactive label
- **THEN** the product response still includes that label's English display name

#### Scenario: Uncategorized product allowed
- **WHEN** a product has no category/tier assigned
- **THEN** `category` and `category_name` are NULL
- **AND** product type and labels still render normally

### Requirement: Product listing endpoint supports faceted taxonomy filters
The public `GET /v1/products` endpoint SHALL filter by managed taxonomy slugs in addition to existing search, stock, sort, pagination, and locale parameters. The endpoint SHALL accept `product_type`, `category`, and labels filters. Filtering SHALL use slugs, independent of localized display names.

#### Scenario: Filter by product type
- **WHEN** `GET /v1/products?product_type=candles` is called
- **THEN** the response contains only products whose product type slug is "candles"

#### Scenario: Filter by category tier
- **WHEN** `GET /v1/products?category=premium` is called
- **THEN** the response contains only products whose category/tier slug is "premium"

#### Scenario: Filter by labels
- **WHEN** `GET /v1/products?labels=winter,gift` is called
- **THEN** the response contains only products assigned both "winter" and "gift" labels

#### Scenario: Filters combine
- **WHEN** `GET /v1/products?product_type=boxes&category=premium&labels=gift` is called
- **THEN** the response contains only premium boxes assigned the "gift" label

#### Scenario: Filtering remains slug-based across locales
- **WHEN** `GET /v1/products?category=medium&locale=bg` is called
- **THEN** filtering matches the stored "medium" slug, independent of the Bulgarian category display name

#### Scenario: Search returns an accurate paginated total
- **WHEN** `GET /v1/products?q=lavender&limit=2&page=1` matches more products than the page size
- **THEN** `total` reflects the full count of matching products (a `COUNT(*)` over the same FTS + filter WHERE clause), not just the number returned on the page
- **AND** the response `products` are limited to the requested page size
