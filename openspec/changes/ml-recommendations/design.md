## Context

AtelierMarie captures behavioral events (product_view, add_to_cart, purchase, impression, click) via `POST /v1/events` into DuckDB. The platform has a product catalog in SQLite (with `is_featured` and `is_active` flags), session tracking via `session_identity` bridge table, and optional Google OAuth for user identity. The system runs on free-tier infrastructure (single process, no Redis, no GPU).

Currently, product discovery is entirely manual — users browse without guidance. The event data exists but isn't used to personalize the experience.

## Goals / Non-Goals

**Goals:**
- Derive all ML features from raw events in DuckDB using pure SQL (reproducible, auditable)
- Serve personalized recommendations with <200ms latency from cache
- Gracefully degrade from personalized → session → popularity → featured (cold-start safe)
- Batch-first architecture: precompute every 30 min, serve from cache
- Keep the system interpretable: weighted linear ranker with transparent "reason" field
- Zero new infrastructure dependencies (no Redis, no GPU, no external services)

**Non-Goals:**
- Real-time model inference or online learning
- Embedding-based retrieval (requires GPU compute)
- ML model training (LightGBM is future Phase 2)
- A/B testing framework (separate concern)
- Recommendation explanations beyond the "reason" field (no natural language explanations)
- Cross-tenant or multi-store recommendations

## Decisions

### 1. DuckDB SQL for all feature engineering

**Choice**: Feature tables computed entirely as DuckDB SQL (DROP + CREATE AS SELECT).

**Alternatives considered**:
- pandas DataFrames: adds dependency, harder to audit, no performance benefit at this scale
- Incremental materialization: complex state management for marginal gain on <10M events

**Rationale**: DuckDB handles <10M events in seconds. SQL is auditable, testable, and requires no additional dependencies. Full rebuild avoids incremental state bugs.

### 2. Weighted linear combination for ranking (Phase 1)

**Choice**: Score = w₁·CTR + w₂·popularity + w₃·diversity_penalty + w₄·price_relevance. Weights configurable via pydantic-settings.

**Alternatives considered**:
- LightGBM model: requires training data volume we don't have yet (>100k labeled events)
- Heuristic sort (popularity only): too simplistic, no personalization

**Rationale**: Linear ranker is interpretable, tunable without retraining, and the feature tables are designed to feed a future model. No cold-start chicken-and-egg problem.

### 3. In-memory dict cache with TTL + LRU eviction

**Choice**: Python dict with per-entry TTL and LRU eviction at 10,000 entries. Each worker process has its own cache (shared-nothing).

**Alternatives considered**:
- Redis: paid service or self-hosted (violates zero-budget constraint)
- SQLite-backed cache: adds write contention to a read-heavy path
- `cachetools` library: viable but trivial to implement ourselves with fewer deps

**Rationale**: Single-process deployment means in-memory is fine. For multi-worker, slight cache inconsistency (each worker warms independently) is acceptable given the 5-30 min TTL window.

### 4. File-lock coordination for batch job

**Choice**: `app/data/.ml-compute.lock` with `fcntl.flock()`, same pattern as existing batch loader.

**Rationale**: DuckDB is single-writer. The ML compute job and event batch loader must not run simultaneously. Shared file-lock pattern keeps coordination simple and consistent.

### 5. Three-stage pipeline architecture

**Choice**: Candidate Generation (broad recall) → Ranking (precision scoring) → Filtering (business rules).

**Rationale**: Industry-standard pattern. Separating stages allows tuning recall vs precision independently, and the filtering stage enforces business logic without polluting the scoring model.

### 6. Fallback chain with explicit thresholds

**Choice**: Personalized (user has ≥20 events) → Session-based (session has ≥3 interactions) → Popularity (system has ≥1000 events) → Featured (cold start).

**Rationale**: Explicit thresholds prevent garbage recommendations from sparse data. The chain guarantees every request gets results, even on day 1 with zero events.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| DuckDB write lock contention between batch loader and ML compute | File lock ensures mutual exclusion; batch loader runs frequently (5s buffer flush) so collisions are brief |
| Feature table rebuild takes >60s as data grows | Monitor computation time in stats; partition by time window if needed; DuckDB handles 10M rows in <30s for these queries |
| Cache staleness (5 min TTL) shows outdated recommendations | Acceptable trade-off for <200ms response; users rarely notice 5-min lag in recommendations |
| Multi-worker cache inconsistency | Each worker warms independently; worst case is slightly different recommendations across requests — not user-facing |
| Cold start with zero events returns only featured products | Acceptable — `is_featured` flag is manually curated specifically for this case |
| Co-occurrence self-join is O(n²) on sessions with many events | HAVING co_count >= 2 prunes noise; session event count is naturally bounded (users don't view 1000 products per session) |

## Open Questions

1. **Should the batch job run on a schedule (cron-like) or only on-demand via CLI?** — Leaning toward both: a background scheduler (using existing event loop or APScheduler-lite) plus CLI trigger for development/debugging.
2. **Cache warming on startup** — Should the first request trigger a full feature rebuild, or should the app start with empty cache and only serve featured/popular until the first batch run completes?
3. **Impression tracking** — CTR features require `impression` events. Are these already emitted by the frontend, or do we need to add impression tracking as a prerequisite?