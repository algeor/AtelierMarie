## 1. Project Structure & Configuration

- [ ] 1.1 Create `app/ml/` package with `__init__.py`
- [ ] 1.2 Create `app/jobs/` package with `__init__.py` (if not existing)
- [ ] 1.3 Add ML configuration to pydantic-settings (ranker weights, TTLs, thresholds, batch interval)

## 2. Feature Engineering

- [ ] 2.1 Implement `app/ml/features.py` — `rebuild_item_popularity()` DuckDB query (time-decayed popularity score, 7-day 2× weighting)
- [ ] 2.2 Implement `rebuild_cooccurrence()` — session co-occurrence matrix with HAVING >= 2 filter
- [ ] 2.3 Implement `rebuild_session_sequences()` — ordered product/event sequences per session (7-day window)
- [ ] 2.4 Implement `rebuild_ctr()` — CTR and conversion rate metrics (30-day window, division-by-zero safe)
- [ ] 2.5 Implement `rebuild_all_features()` orchestrator — DROP+CREATE for all tables in dependency order
- [ ] 2.6 Write tests for feature engineering queries (mock DuckDB with test events)

## 3. Recommendation Cache

- [ ] 3.1 Implement `app/ml/cache.py` — `RecommendationCache` class with per-key-type TTL (session=5min, user=30min, trending=30min)
- [ ] 3.2 Implement LRU eviction logic (max 10,000 entries, trending/featured exempt)
- [ ] 3.3 Implement cache statistics (hit/miss/eviction counts, current size)
- [ ] 3.4 Write tests for cache TTL expiry, LRU eviction, and multi-type storage

## 4. Candidate Generation

- [ ] 4.1 Implement `app/ml/candidates.py` — `generate_similarity_candidates()` from co-occurrence table
- [ ] 4.2 Implement `generate_session_candidates()` from session sequence patterns
- [ ] 4.3 Implement `generate_trending_candidates()` from popularity scores
- [ ] 4.4 Implement `generate_candidates()` orchestrator — merge, deduplicate, cap at ~100
- [ ] 4.5 Write tests for candidate generation (each source independently + merged)

## 5. Ranking

- [ ] 5.1 Implement `app/ml/ranker.py` — `score_candidates()` with weighted linear combination (CTR, popularity, diversity, price relevance)
- [ ] 5.2 Implement category diversity penalty (first=1.0, second=0.5, third=0.25)
- [ ] 5.3 Implement price range relevance scoring (based on session's viewed price range)
- [ ] 5.4 Implement normalization of component scores to 0-1 range
- [ ] 5.5 Write tests for ranker with various weight configurations

## 6. Filtering & Recommender Orchestration

- [ ] 6.1 Implement filtering logic — remove already-viewed, inactive products, category cap (max 3 per category)
- [ ] 6.2 Implement `app/ml/recommender.py` — `get_recommendations()` with fallback chain (personalized → session → popularity → featured)
- [ ] 6.3 Implement threshold checks: `user_has_enough_history(min=20)`, `session_has_interactions(min=3)`, `system_has_enough_data(min=1000)`
- [ ] 6.4 Implement `reason` assignment for each recommendation (similar_to_viewed, frequently_bought_together, trending, session_pattern, popular, featured)
- [ ] 6.5 Write tests for fallback chain logic (each level triggered correctly)

## 7. Batch Computation Job

- [ ] 7.1 Implement `app/jobs/ml_compute.py` — file lock acquisition at `app/data/.ml-compute.lock`
- [ ] 7.2 Implement batch job orchestration: rebuild features → precompute recommendations → update cache
- [ ] 7.3 Implement stats logging (duration, rows per table, sessions precomputed, status)
- [ ] 7.4 Implement CLI entry point (`python -m app.jobs.ml_compute`)
- [ ] 7.5 Implement scheduled execution (30-min interval via background task or startup hook)
- [ ] 7.6 Write tests for batch job (lock behavior, error handling, stats output)

## 8. Recommendation API

- [ ] 8.1 Implement `app/api/v1/recommendations.py` — `GET /v1/recommendations` endpoint with session header + optional auth
- [ ] 8.2 Implement query parameter handling (n, context_product_id) with validation (max 50)
- [ ] 8.3 Implement `GET /v1/recommendations/trending` endpoint (no auth/session required)
- [ ] 8.4 Implement response models (Pydantic): recommendation items, strategy field, cached flag
- [ ] 8.5 Register router in main FastAPI app
- [ ] 8.6 Write integration tests for both endpoints (cache hit, cache miss, error cases)

## 9. Integration & Verification

- [ ] 9.1 End-to-end test: ingest events → run batch job → query recommendations API
- [ ] 9.2 Verify file lock coordination between ML compute and existing batch loader
- [ ] 9.3 Verify <200ms response from cache and <2s on cache miss
- [ ] 9.4 Verify fallback chain returns featured products with zero events (cold start)
