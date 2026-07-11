## MODIFIED Requirements

### Requirement: Product service searches products by text
The product service SHALL perform full-text search across product name and description using SQLite FTS5. User search input SHALL be sanitized by wrapping each whitespace-separated token in double quotes before passing to FTS5. This prevents interpretation of FTS5 operators (AND, OR, NOT, NEAR, *, ^) as anything other than literal text. The service SHALL return results ranked by relevance. Only active products SHALL appear in results.

#### Scenario: Search matching products
- **WHEN** `search_products("lavender")` is called and products with "lavender" in name or description exist
- **THEN** matching active products are returned sorted by FTS5 relevance rank

#### Scenario: Search with no matches
- **WHEN** `search_products("xyznonexistent")` is called
- **THEN** an empty list is returned

#### Scenario: Search excludes inactive products
- **WHEN** `search_products("discontinued")` is called and the matching product has `is_active=0`
- **THEN** an empty list is returned

#### Scenario: Search with FTS5 operators treated as literal text
- **WHEN** `search_products("lavender OR poison")` is called
- **THEN** the system searches for literal words "lavender", "OR", "poison" — the OR is NOT treated as a boolean operator

#### Scenario: Search with wildcard treated as literal
- **WHEN** `search_products("lav*")` is called
- **THEN** the asterisk is treated as literal text (quoted), not as a prefix wildcard operator

### Requirement: Product service lists active products with pagination
The product service SHALL return a paginated list of active products. The service SHALL accept optional filters for category, in-stock-only, and a sort parameter. Default sort SHALL be by `created_at` descending (newest first). The service SHALL return the total count of matching products alongside the page of results. The page number SHALL be clamped to a maximum of 10,000 and limit SHALL be clamped to a maximum of 100.

#### Scenario: List products with default parameters
- **WHEN** `list_products()` is called with no filters
- **THEN** the service returns up to 20 active products sorted by created_at descending, with total count

#### Scenario: Excessive page number is clamped
- **WHEN** `list_products(page=9999999)` is called
- **THEN** the service uses page=10000 (the maximum), not page=9999999

#### Scenario: Excessive limit is clamped
- **WHEN** `list_products(limit=5000)` is called
- **THEN** the service uses limit=100 (the maximum)

#### Scenario: Pagination returns correct slice
- **WHEN** `list_products(page=2, limit=5)` is called with 12 matching products
- **THEN** products 6–10 are returned with total=12, page=2, limit=5
