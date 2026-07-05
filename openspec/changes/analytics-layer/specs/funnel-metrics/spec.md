## ADDED Requirements

### Requirement: Funnel metrics materialized table
The analytics layer SHALL compute an `analytics_funnel` summary table in DuckDB containing conversion funnel metrics for the last 30 days.

The table MUST be a single-row result containing: `total_views`, `total_carts`, `total_checkouts`, `total_purchases`, `unique_sessions`, `conversion_rate`, `cart_rate`, and `total_revenue`.

#### Scenario: Conversion rate computed
- **WHEN** the analytics job runs
- **AND** there are 1000 unique sessions and 50 purchase events
- **THEN** conversion_rate equals 0.05 (50/1000)

#### Scenario: Cart rate computed
- **WHEN** the analytics job runs
- **AND** there are 1000 unique sessions and 200 add_to_cart events
- **THEN** cart_rate equals 0.20 (200/1000)

#### Scenario: Division by zero handled
- **WHEN** unique_sessions is 0
- **THEN** conversion_rate and cart_rate are both 0.0

#### Scenario: Revenue from completed orders
- **WHEN** purchase events reference order totals in metadata
- **THEN** total_revenue sums all purchase event amounts
