## MOVED Requirements

> **These requirements have been moved to the `analytics-layer` change.**
>
> Feature engineering is now owned by the shared analytics layer, which materializes tables consumed by multiple services (ML recommendations, admin dashboard, storefront).
>
> See:
> - `openspec/changes/analytics-layer/specs/product-metrics/spec.md` (was: item popularity)
> - `openspec/changes/analytics-layer/specs/cooccurrence/spec.md` (was: co-occurrence)
> - `openspec/changes/analytics-layer/specs/session-sequences/spec.md` (was: session sequences)
> - `openspec/changes/analytics-layer/specs/ctr-metrics/spec.md` (was: CTR)
>
> The ML recommendations service is now a **read-only consumer** of these tables.

## ADDED Requirements

### Requirement: ML service reads from analytics tables
The recommendation service SHALL read features exclusively from `analytics_*` tables in DuckDB. It SHALL NOT compute its own feature aggregations from the raw events table.

#### Scenario: Popularity features read from analytics layer
- **WHEN** the recommendation service needs popularity scores
- **THEN** it reads from `analytics_popularity` (not a self-computed table)

#### Scenario: Co-occurrence features read from analytics layer
- **WHEN** the recommendation service generates candidates via co-occurrence
- **THEN** it reads from `analytics_cooccurrence`

#### Scenario: CTR features read from analytics layer
- **WHEN** the recommendation service ranks candidates by CTR
- **THEN** it reads from `analytics_ctr`

#### Scenario: Session sequences read from analytics layer
- **WHEN** the recommendation service uses session-based recommendations
- **THEN** it reads from `analytics_session_sequences`

#### Scenario: Analytics tables unavailable (first startup)
- **WHEN** analytics tables do not yet exist (e.g., first app start before analytics job runs)
- **THEN** the recommendation service falls through to the featured products fallback
