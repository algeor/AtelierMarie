## ADDED Requirements

### Requirement: Public product recommendations API
The backend SHALL expose a public recommendations endpoint for a selected active product.

#### Scenario: Recommendations returned for active product
- **WHEN** `GET /v1/products/{product_id}/recommendations` is requested for an active product with related active candidates
- **THEN** the response contains recommended products and pagination metadata

#### Scenario: Current product excluded
- **WHEN** recommendations are requested for a product
- **THEN** the selected product is not included in the returned products

#### Scenario: Inactive products excluded
- **WHEN** inactive products match recommendation rules
- **THEN** inactive products are excluded from the returned recommendations

#### Scenario: Unknown product returns not found
- **WHEN** recommendations are requested for a missing or inactive product ID
- **THEN** the API returns the same not-found error behavior as public product detail

#### Scenario: Empty recommendations are valid
- **WHEN** no eligible recommendation candidates exist
- **THEN** the API returns an empty product list with total `0`

### Requirement: Rule-based recommendations work without embeddings
The backend SHALL provide deterministic recommendations using product metadata before semantic scoring is added.

#### Scenario: Shared taxonomy increases ranking
- **WHEN** candidate products share product type, category, or labels with the selected product
- **THEN** those shared signals increase the candidate recommendation score

#### Scenario: Orderability influences ranking
- **WHEN** eligible candidates differ by stock/orderability or featured status
- **THEN** orderable and featured products can be boosted without allowing inactive products into results

#### Scenario: Stable tie-breaks
- **WHEN** two candidate products have the same recommendation score
- **THEN** the system applies a stable tie-break such as featured status, created date, and product ID

#### Scenario: Rule-only fallback is authoritative
- **WHEN** no embedding data exists
- **THEN** the recommendations endpoint still returns rule-ranked recommendations where possible

### Requirement: Recommendation request limits are bounded
The recommendations API SHALL enforce bounded limits to protect query cost.

#### Scenario: Default limit applied
- **WHEN** recommendations are requested without a limit
- **THEN** the system returns a default bounded number of recommendations

#### Scenario: Excessive limit is clamped
- **WHEN** recommendations are requested with a limit above the supported maximum
- **THEN** the system clamps the limit to the maximum supported value

#### Scenario: Invalid limit rejected or normalized
- **WHEN** recommendations are requested with an invalid limit
- **THEN** the system rejects the request with validation feedback or normalizes to a safe default

### Requirement: API recommendation tests cover public behavior
The backend SHALL include service and route tests for the public recommendation behavior.

#### Scenario: Route test covers successful recommendations
- **WHEN** a route test requests recommendations for a seeded product
- **THEN** it verifies the response contains only eligible recommended products

#### Scenario: Service test covers ranking
- **WHEN** a service test seeds candidates with different taxonomy overlap
- **THEN** it verifies higher-overlap candidates rank above lower-overlap candidates

#### Scenario: Route test covers not found
- **WHEN** a route test requests recommendations for a missing product
- **THEN** it verifies the not-found response
