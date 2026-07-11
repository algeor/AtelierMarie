## ADDED Requirements

### Requirement: Row model for every analytics table
The system SHALL define a Pydantic model in `app/contracts/analytics.py` for each `analytics_*` materialized table. The model field names MUST exactly match the SQL column names. The model field types MUST match the DuckDB column types after Python coercion.

#### Scenario: ProductMetricsRow matches analytics_product_metrics
- **WHEN** the analytics compute job creates `analytics_product_metrics`
- **THEN** every row validates against `ProductMetricsRow(product_id: str, view_count: int, cart_count: int, purchase_count: int, unique_sessions: int, revenue: Decimal)`

#### Scenario: FunnelRow matches analytics_funnel
- **WHEN** the analytics compute job creates `analytics_funnel`
- **THEN** the single row validates against `FunnelRow(total_views: int, total_carts: int, total_checkouts: int, total_purchases: int, unique_sessions: int, conversion_rate: Decimal, cart_rate: Decimal, total_revenue: Decimal)`

#### Scenario: CooccurrenceRow matches analytics_cooccurrence
- **WHEN** the analytics compute job creates `analytics_cooccurrence`
- **THEN** every row validates against `CooccurrenceRow(product_a: str, product_b: str, co_count: int)`

#### Scenario: CtrRow matches analytics_ctr
- **WHEN** the analytics compute job creates `analytics_ctr`
- **THEN** every row validates against `CtrRow(product_id: str, impressions: int, clicks: int, purchases: int, ctr: Decimal, conversion_rate: Decimal)`

#### Scenario: PopularityRow matches analytics_popularity
- **WHEN** the analytics compute job creates `analytics_popularity`
- **THEN** every row validates against `PopularityRow(product_id: str, popularity_score: Decimal, view_count: int, cart_count: int, purchase_count: int, unique_sessions: int, recency_boost: Decimal)`

#### Scenario: SessionMetricsRow matches analytics_session_metrics
- **WHEN** the analytics compute job creates `analytics_session_metrics`
- **THEN** the single row validates against `SessionMetricsRow(total_sessions: int, anonymous_sessions: int, authenticated_sessions: int, converted_sessions: int, avg_events_per_session: Decimal)`

#### Scenario: SearchTermRow matches analytics_search_terms
- **WHEN** the analytics compute job creates `analytics_search_terms`
- **THEN** every row validates against `SearchTermRow(query: str, search_count: int, avg_result_count: Decimal)`

#### Scenario: SessionSequenceRow matches analytics_session_sequences
- **WHEN** the analytics compute job creates `analytics_session_sequences`
- **THEN** every row validates against `SessionSequenceRow(session_id: str, product_sequence: list[str], event_sequence: list[str])`

---

### Requirement: Analytics table registry maps table names to row models
The system SHALL maintain an `ANALYTICS_TABLE_MAP` dictionary that maps every `analytics_*` table name to its corresponding Pydantic row model class.

#### Scenario: Every analytics table has a mapping
- **WHEN** a test queries DuckDB for all tables matching `analytics_%`
- **THEN** every discovered table name exists as a key in `ANALYTICS_TABLE_MAP`

#### Scenario: Adding a new analytics table without a row model fails tests
- **WHEN** a developer adds a new SQL file that creates `analytics_bounce_rate`
- **AND** does NOT add a corresponding entry in `ANALYTICS_TABLE_MAP`
- **THEN** `test_all_analytics_tables_have_contracts` fails

#### Scenario: Registry is iterable for programmatic testing
- **WHEN** the contract test suite runs
- **THEN** it iterates `ANALYTICS_TABLE_MAP` and for each entry, runs `DESCRIBE {table_name}` and asserts column names match the model's field names

---

### Requirement: SQL output schema validated against row model
The system SHALL include a test that executes each analytics SQL file against a test DuckDB instance and validates that the output columns exactly match the corresponding row model's fields (name and compatible type).

#### Scenario: Column names match model fields
- **WHEN** `analytics_product_metrics` has columns `[product_id, view_count, cart_count, purchase_count, unique_sessions, revenue]`
- **THEN** `ProductMetricsRow.model_fields.keys()` equals that set exactly
- **AND** the test passes

#### Scenario: SQL adds a column not in model → test fails
- **WHEN** a developer adds `avg_price` column to the product_metrics SQL
- **AND** does NOT add `avg_price` to `ProductMetricsRow`
- **THEN** the contract test fails with: "analytics_product_metrics has column 'avg_price' not in ProductMetricsRow"

#### Scenario: Model has a field not in SQL → test fails
- **WHEN** `ProductMetricsRow` has a field `click_count` that the SQL does not produce
- **THEN** the contract test fails with: "ProductMetricsRow has field 'click_count' not in analytics_product_metrics"

---

### Requirement: Consumers import row models for type-safe access
The system SHALL require that all Python code reading from analytics tables wraps results in the corresponding row model. Raw dict access (`row["column"]`) is prohibited in consumer code.

#### Scenario: ML recommender uses typed access
- **WHEN** the ML batch job reads from `analytics_popularity`
- **THEN** it constructs `PopularityRow(**row)` for each result
- **AND** accesses fields via `row.popularity_score` (not `row["popularity_score"]`)

#### Scenario: Admin dashboard uses typed access
- **WHEN** the admin dashboard route reads from `analytics_funnel`
- **THEN** it constructs `FunnelRow(**row)` for the result
- **AND** accesses fields via `row.total_revenue` (not `row["total_revenue"]`)

#### Scenario: Invalid row shape raises ValidationError immediately
- **WHEN** a DuckDB query returns a row missing the `revenue` field
- **AND** consumer code wraps it in `ProductMetricsRow(**row)`
- **THEN** a `ValidationError` is raised at the point of construction
- **AND** the error is not silently propagated downstream

---

### Requirement: Event payload fields traced to analytics SQL usage
The system SHALL include a test that parses analytics SQL files for `metadata->>'field_name'` patterns and asserts that each extracted field exists in the payload model for the event types that SQL file filters on.

#### Scenario: SQL extracts 'price' from purchase events → payload has 'price'
- **WHEN** the product_metrics SQL contains `metadata->>'price'`
- **AND** the SQL filters on `event_type = 'purchase'`
- **THEN** the test asserts `'price' in PurchasePayload.model_fields`
- **AND** the test passes

#### Scenario: SQL extracts 'query' from search events → payload has 'query'
- **WHEN** the search_terms SQL contains `metadata->>'query'`
- **AND** the SQL filters on `event_type = 'search'`
- **THEN** the test asserts `'query' in SearchPayload.model_fields`
- **AND** the test passes

#### Scenario: SQL extracts field not in payload model → test fails
- **WHEN** a developer writes SQL that extracts `metadata->>'discount_pct'` for purchase events
- **AND** `PurchasePayload` does not have a `discount_pct` field
- **THEN** `test_event_payloads_cover_analytics_assumptions` fails
- **AND** the error message says: "SQL uses metadata->>'discount_pct' for event_type 'purchase' but PurchasePayload has no field 'discount_pct'"
