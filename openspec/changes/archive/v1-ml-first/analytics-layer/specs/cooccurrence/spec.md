## ADDED Requirements

### Requirement: Co-occurrence materialized table
The analytics layer SHALL compute an `analytics_cooccurrence` table containing pairs of products that appear together within the same session, considering product_view, add_to_cart, and purchase event types from the last 30 days.

Each pair MUST appear only once (product_a < product_b lexicographically) with a `co_count` of at least 2.

#### Scenario: Products co-viewed in same session
- **WHEN** products A and B are both viewed in 3 different sessions within the last 30 days
- **THEN** the table contains a row (product_a=A, product_b=B, co_count=3) assuming A < B

#### Scenario: Single co-occurrence filtered out
- **WHEN** products A and B co-occur in only 1 session
- **THEN** the pair does NOT appear (HAVING co_count >= 2)

#### Scenario: Different event types count
- **WHEN** product A is viewed and product B is purchased in the same session
- **THEN** this counts as one co-occurrence (both event types qualify)

#### Scenario: Rebuild is idempotent
- **WHEN** the analytics job runs twice with no new events between runs
- **THEN** `analytics_cooccurrence` contains identical data
