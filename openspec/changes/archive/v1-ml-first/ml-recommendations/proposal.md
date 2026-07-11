## Why

The AtelierMarie platform captures rich behavioral events (views, cart additions, purchases) but doesn't yet leverage them to drive product discovery. Without recommendations, users must manually browse the catalog — reducing conversion and engagement. The event pipeline and product catalog are already built; the ML layer is the natural next step to turn raw behavioral data into personalized shopping experiences, all within zero-budget constraints.

## What Changes

- Add **feature engineering** pipeline: DuckDB SQL queries that materialize item popularity, co-occurrence matrices, session sequences, and CTR metrics into feature tables
- Add **recommendation pipeline**: three-stage system (candidate generation → ranking → filtering) with a configurable weighted linear ranker
- Add **cold-start fallback chain**: graceful degradation from personalized → session-based → popularity → featured products
- Add **batch computation job**: background task (every 30 min) that rebuilds feature tables and precomputes recommendations, using file-lock pattern
- Add **recommendation API**: `GET /v1/recommendations` (personalized) and `GET /v1/recommendations/trending` (global trending)
- Add **in-memory caching layer**: TTL-based LRU cache for session, user, and trending recommendations

## Capabilities

### New Capabilities

- `feature-engineering`: DuckDB-based feature computation — item popularity, co-occurrence, session sequences, CTR — materialized as feature tables with DROP+CREATE rebuild
- `recommendation-pipeline`: Three-stage recommendation system (candidate generation, ranking, filtering) with configurable weighted linear scoring and cold-start fallback chain
- `recommendation-api`: REST endpoints for personalized and trending recommendations, including session context, caching metadata, and strategy transparency
- `ml-batch-job`: Background batch computation job with file-lock coordination, feature table rebuild, precomputation of recommendations, and stats logging
- `recommendation-cache`: In-memory TTL+LRU cache for recommendations with per-key-type TTLs (session: 5min, user: 30min, trending: 30min)

### Modified Capabilities

_(none — no existing specs are affected)_

## Impact

- **New code**: `app/ml/` package (features, candidates, ranker, recommender, cache), `app/api/v1/recommendations.py`, `app/jobs/ml_compute.py`
- **DuckDB schema**: New feature tables (`features_item_popularity`, `features_cooccurrence`, `features_session_sequences`, `features_ctr`) alongside existing `events` table
- **API surface**: Two new GET endpoints under `/v1/recommendations`
- **Dependencies**: None for Phase 1 (pure Python + DuckDB SQL). Future phases may add `lightgbm`, `scikit-learn`
- **Infrastructure**: File lock at `app/data/.ml-compute.lock` (matches existing batch loader pattern)
- **Performance**: Batch job must complete <60s for <1M events; API response <200ms from cache
