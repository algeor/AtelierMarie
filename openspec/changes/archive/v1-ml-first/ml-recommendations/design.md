## Context

AtelierMarie captures behavioral events (product_view, add_to_cart, purchase, impression, click) via `POST /v1/events` into DuckDB. The platform has a product catalog in SQLite (with `is_featured` and `is_active` flags), session tracking via `session_identity` bridge table, and optional Google OAuth for user identity. The system runs on free-tier infrastructure (single process, no Redis, no GPU).

A shared **analytics layer** (see `analytics-layer` change) now materializes feature tables (`analytics_popularity`, `analytics_cooccurrence`, `analytics_session_sequences`, `analytics_ctr`) from raw events on a scheduled basis. Multiple consumers — including this ML recommendations service, the admin dashboard, and the storefront — read from these pre-materialized tables.

Currently, product discovery is entirely manual — users browse without guidance. The event data exists but isn't used to personalize the experience.

## Goals / Non-Goals

**Goals:**
- Read ML features from the shared analytics layer's pre-materialized tables in DuckDB
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

### 1. Consume shared analytics layer

**Choice**: The ML service reads from pre-materialized `analytics_*` tables (popularity, co-occurrence, session sequences, CTR) instead of computing features itself. Feature engineering is owned by the shared analytics layer (see `analytics-layer` change).

**Alternatives considered**:
- Compute features within ML service (original design): duplicates logic needed by other consumers (dashboard, storefront)
- Event-sourced per-request computation: too slow for <200ms latency target

**Rationale**: Centralizing feature computation in the analytics layer avoids duplication, ensures consistency across consumers, and simplifies the ML service to a read-only consumer. The analytics layer handles scheduling, write locks, and rebuild semantics.

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

### 4. No write lock needed — read-only consumer

**Choice**: The ML recommendations service acquires no file lock. It only reads from `analytics_*` tables in DuckDB and writes precomputed recommendation lists to its own in-memory cache.

**Rationale**: Since the ML service no longer writes to DuckDB, there is no write contention with the event batch loader or analytics layer. The batch job that precomputes recommendation lists operates purely in-memory (read analytics tables → compute top-N → store in Python dict cache). No `.ml-compute.lock` is needed.

### 5. Three-stage pipeline architecture

**Choice**: Candidate Generation (broad recall) → Ranking (precision scoring) → Filtering (business rules).

**Rationale**: Industry-standard pattern. Separating stages allows tuning recall vs precision independently, and the filtering stage enforces business logic without polluting the scoring model.

### 6. Fallback chain with explicit thresholds

**Choice**: Personalized (user has ≥20 events) → Session-based (session has ≥3 interactions) → Popularity (system has ≥1000 events) → Featured (cold start).

**Rationale**: Explicit thresholds prevent garbage recommendations from sparse data. The chain guarantees every request gets results, even on day 1 with zero events.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Analytics layer staleness (if analytics job fails, ML serves stale features) | Fallback chain ensures degradation to featured products if analytics tables are missing or empty; staleness is bounded by analytics job schedule (30 min) |
| Feature table rebuild takes >60s as data grows | Monitor computation time in stats; partition by time window if needed; DuckDB handles 10M rows in <30s for these queries |
| Cache staleness (5 min TTL) shows outdated recommendations | Acceptable trade-off for <200ms response; users rarely notice 5-min lag in recommendations |
| Multi-worker cache inconsistency | Each worker warms independently; worst case is slightly different recommendations across requests — not user-facing |
| Cold start with zero events returns only featured products | Acceptable — `is_featured` flag is manually curated specifically for this case |
| Co-occurrence self-join is O(n²) on sessions with many events | HAVING co_count >= 2 prunes noise; session event count is naturally bounded (users don't view 1000 products per session) |

## Open Questions

1. **Should the batch job run on a schedule (cron-like) or only on-demand via CLI?** — Leaning toward both: a background scheduler (using existing event loop or APScheduler-lite) plus CLI trigger for development/debugging.
2. **Cache warming on startup** — Should the first request trigger a full feature rebuild, or should the app start with empty cache and only serve featured/popular until the first batch run completes?
3. **Impression tracking** — CTR features require `impression` events. Are these already emitted by the frontend, or do we need to add impression tracking as a prerequisite?
