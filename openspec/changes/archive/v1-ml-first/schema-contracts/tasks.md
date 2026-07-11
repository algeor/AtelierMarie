# Schema Contracts — Tasks

## Phase 1: Event Contracts

- [ ] 1.1 Create `app/contracts/__init__.py` with public re-exports
- [ ] 1.2 Create `app/contracts/events.py` with `EventType` enum (all 10 event types)
- [ ] 1.3 Define payload models: `ProductViewPayload`, `SearchPayload`, `AddToCartPayload`, `PurchasePayload`, `ImpressionPayload`, `ClickPayload`, `EmptyPayload`
- [ ] 1.4 Define `EVENT_PAYLOAD_MAP` registry (EventType → PayloadModel)
- [ ] 1.5 Refactor event ingestion endpoint to validate `metadata` against the correct payload model based on `event_type`
- [ ] 1.6 Ensure validated (coerced) payload is serialized to JSONL (not raw input)
- [ ] 1.7 Write `test_every_event_type_has_payload_model` (coverage assertion)
- [ ] 1.8 Write unit tests for each payload model (valid + invalid inputs)

## Phase 2: Analytics Table Contracts

- [ ] 2.1 Create `app/contracts/analytics.py` with all 8 row models
- [ ] 2.2 Define `ANALYTICS_TABLE_MAP` registry (table_name → RowModel)
- [ ] 2.3 Write `test_analytics_tables_match_row_models` (DESCRIBE vs model fields)
- [ ] 2.4 Write `test_event_payloads_cover_analytics_assumptions` (SQL metadata extraction → payload field assertion)
- [ ] 2.5 Refactor ML recommender to wrap DuckDB results in row models (type-safe access)
- [ ] 2.6 Refactor admin dashboard routes to wrap DuckDB results in row models

## Phase 3: API Response Contracts

- [ ] 3.1 Create `app/contracts/api.py` with shared response models (ProductListItem, ProductDetail, PaginatedProducts, AdminProductItem, DashboardMetrics, OrderResponse, CartResponse, ErrorResponse)
- [ ] 3.2 Configure all response models with `extra="forbid"`
- [ ] 3.3 Refactor route handlers to use `response_model=ContractModel` from contracts module
- [ ] 3.4 Write `test_api_responses_are_strict` (all models have extra=forbid)
- [ ] 3.5 Write integration tests that validate live endpoint responses against contract models
- [ ] 3.6 Document API versioning policy in `app/contracts/README.md` (additive-only rules)

## Phase 4: Cross-Cutting Contract Tests

- [ ] 4.1 Write `test_all_analytics_tables_have_contracts` (discover analytics_* tables in DuckDB → assert mapping exists)
- [ ] 4.2 Write SQL-parsing test that extracts `metadata->>'field'` patterns from SQL files and validates against payload models
- [ ] 4.3 Add contract tests to CI pipeline (pytest marker: `@pytest.mark.contracts`)
- [ ] 4.4 Write `test_openapi_schema_matches_contracts` (fetch /openapi.json, validate response schemas match model definitions)
