## ADDED Requirements

### Requirement: Item popularity feature table
The system SHALL compute an `features_item_popularity` table in DuckDB containing per-product engagement metrics derived from the events table, covering the last 30 days of data.

The table MUST include: `product_id`, `view_count`, `cart_count`, `purchase_count`, `unique_sessions`, and a `popularity_score` that weights recent activity (last 7 days) at 2× relative to older activity (8-30 days).

#### Scenario: Popularity computed from mixed events
- **WHEN** a product has 100 views, 20 cart additions, and 5 purchases in the last 30 days
- **THEN** the feature table contains a row with product_id, view_count=100, cart_count=20, purchase_count=5, and a computed popularity_score

#### Scenario: Time decay weighting
- **WHEN** a product has 50 views in the last 7 days and 50 views in days 8-30
- **THEN** the popularity_score weights the recent 50 views at 2× (equivalent to 100) plus the older 50 views, for a total weighted view contribution of 150

#### Scenario: No events for a product
- **WHEN** a product has no events in the last 30 days
- **THEN** the product does NOT appear in the features_item_popularity table

### Requirement: Co-occurrence feature table
The system SHALL compute a `features_cooccurrence` table containing pairs of products that appear together within the same session, considering only product_view, add_to_cart, and purchase event types from the last 30 days.

Each pair MUST appear only once (product_a < product_b) with a `co_count` of at least 2.

#### Scenario: Products co-viewed in same session
- **WHEN** products A and B are both viewed in 3 different sessions within the last 30 days
- **THEN** the co-occurrence table contains a row (product_a=A, product_b=B, co_count=3) assuming A < B lexicographically

#### Scenario: Single co-occurrence filtered out
- **WHEN** products A and B co-occur in only 1 session
- **THEN** the pair does NOT appear in the features_cooccurrence table (HAVING co_count >= 2)

#### Scenario: Different event types count
- **WHEN** product A is viewed and product B is purchased in the same session
- **THEN** this counts as one co-occurrence (both event types qualify)

### Requirement: Session sequences feature table
The system SHALL compute a `features_session_sequences` table containing ordered product interaction sequences per session from the last 7 days.

Each row MUST contain: `session_id`, `product_sequence` (list of product_ids ordered by timestamp), and `event_sequence` (list of corresponding event types).

#### Scenario: Session with multiple product interactions
- **WHEN** a session views product A, then adds product B to cart, then views product C
- **THEN** the session_sequences table contains product_sequence=[A, B, C] and event_sequence=[product_view, add_to_cart, product_view]

#### Scenario: Events without product_id excluded
- **WHEN** a session has events with and without product_id
- **THEN** only events with a non-NULL product_id appear in the sequences

### Requirement: CTR feature table
The system SHALL compute a `features_ctr` table containing per-product impression, click, and purchase counts from the last 30 days, plus derived CTR and conversion rate metrics.

#### Scenario: CTR calculated from impressions and clicks
- **WHEN** a product has 1000 impressions and 50 clicks
- **THEN** the ctr field equals 0.05 (50/1000)

#### Scenario: Zero impressions
- **WHEN** a product has 0 impressions
- **THEN** the ctr field equals 0 (no division by zero)

#### Scenario: Conversion rate calculated
- **WHEN** a product has 50 clicks and 5 purchases
- **THEN** the conversion_rate field equals 0.1 (5/50)

### Requirement: Feature tables are fully rebuilt
The system SHALL rebuild all feature tables using DROP TABLE IF EXISTS followed by CREATE TABLE AS SELECT. Feature tables are NEVER incrementally updated.

#### Scenario: Rebuild replaces stale data
- **WHEN** the feature rebuild runs and new events have arrived since the last rebuild
- **THEN** all feature tables reflect the current state of the events table (no stale rows from previous computation)

#### Scenario: Rebuild is idempotent
- **WHEN** the feature rebuild runs twice in succession with no new events
- **THEN** the feature tables contain identical data after both runs