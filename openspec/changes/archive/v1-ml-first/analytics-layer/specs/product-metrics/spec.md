## ADDED Requirements

### Requirement: Product metrics materialized table
The analytics layer SHALL compute an `analytics_product_metrics` table in DuckDB containing per-product engagement metrics derived from the events table, covering the last 30 days.

The table MUST include: `product_id`, `view_count`, `cart_count`, `purchase_count`, `unique_sessions`, and `revenue`.

#### Scenario: Metrics computed from mixed events
- **WHEN** the analytics job runs
- **AND** a product has 100 product_view events, 20 add_to_cart events, and 5 purchase events in the last 30 days
- **THEN** `analytics_product_metrics` contains a row with product_id, view_count=100, cart_count=20, purchase_count=5

#### Scenario: Revenue computed from purchase events
- **WHEN** the analytics job runs
- **AND** a product has 5 purchases with prices [20.00, 20.00, 25.00, 20.00, 20.00]
- **THEN** the revenue field equals 105.00

#### Scenario: Unique sessions counted
- **WHEN** a product is viewed 10 times across 3 different sessions
- **THEN** unique_sessions equals 3

#### Scenario: No events for a product
- **WHEN** a product has no events in the last 30 days
- **THEN** the product does NOT appear in `analytics_product_metrics`

#### Scenario: Table is fully rebuilt each run
- **WHEN** the analytics job runs
- **THEN** `analytics_product_metrics` is dropped and recreated (not incrementally updated)
