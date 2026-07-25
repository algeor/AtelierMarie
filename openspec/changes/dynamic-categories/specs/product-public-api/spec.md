## MODIFIED Requirements

### Requirement: Product responses expose managed category display names
Public product list and detail responses SHALL keep `category` as the stored category slug used for filtering, and SHALL include `category_name` as the localized display name resolved from managed categories for the requested locale. The category display lookup SHALL include inactive categories so retired categories still render correctly on products that reference them. If the category row is missing, `category_name` SHALL fall back to the raw slug for compatibility.

#### Scenario: List response includes localized category name
- **WHEN** `GET /v1/products?locale=bg` returns a product with `category` = "floral"
- **THEN** that product includes `category` = "floral"
- **AND** `category_name` is the Bulgarian category name when present, otherwise the English category name

#### Scenario: Detail response includes inactive category name
- **WHEN** `GET /v1/products/{id}?locale=en` returns a product assigned to an inactive category
- **THEN** the product response still includes the inactive category's English `category_name`

#### Scenario: Filtering remains slug-based
- **WHEN** `GET /v1/products?category=floral&locale=bg` is called
- **THEN** filtering matches products whose stored `category` slug is "floral", independent of the localized `category_name`
