## ADDED Requirements

### Requirement: CTR metrics materialized table
The analytics layer SHALL compute an `analytics_ctr` table containing per-product impression, click, and purchase counts from the last 30 days, plus derived CTR and conversion rate metrics.

#### Scenario: CTR calculated from impressions and clicks
- **WHEN** a product has 1000 impression events and 50 click events
- **THEN** ctr equals 0.05 (50/1000)

#### Scenario: Zero impressions
- **WHEN** a product has 0 impressions
- **THEN** ctr equals 0.0 (no division by zero)

#### Scenario: Conversion rate from clicks to purchases
- **WHEN** a product has 50 clicks and 5 purchase events
- **THEN** conversion_rate equals 0.10 (5/50)

#### Scenario: Products without any interaction excluded
- **WHEN** a product has no impression, click, or purchase events in the last 30 days
- **THEN** it does NOT appear in `analytics_ctr`
