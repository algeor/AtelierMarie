# Analytics Layer — Tasks

## Phase 1: Foundation

- [ ] Create `app/analytics/` package with `__init__.py`
- [ ] Create `app/analytics/compute.py` — orchestrator that runs tier1 + conditional tier2
- [ ] Create `app/analytics/scheduler.py` — 5-minute background loop with tier2 time gate
- [ ] Create `app/analytics/queries/` directory for SQL files
- [ ] Add analytics configuration to `app/config.py` (tier1_interval, tier2_interval, lock_timeout)

## Phase 2: Tier 1 SQL Queries

- [ ] Write `app/analytics/queries/product_metrics.sql` — product view/cart/purchase/session/revenue aggregates (30d)
- [ ] Write `app/analytics/queries/session_metrics.sql` — session breakdown by auth state (30d)
- [ ] Write `app/analytics/queries/search_terms.sql` — normalized search term frequency + avg results (30d)
- [ ] Write `app/analytics/queries/funnel.sql` — conversion funnel metrics (30d)

## Phase 3: Tier 2 SQL Queries

- [ ] Write `app/analytics/queries/popularity.sql` — time-decay popularity scoring (7d boost, 30d window)
- [ ] Write `app/analytics/queries/cooccurrence.sql` — session co-occurrence pairs with min threshold (30d)
- [ ] Write `app/analytics/queries/session_sequences.sql` — ordered product interaction sequences (7d)
- [ ] Write `app/analytics/queries/ctr.sql` — impression/click/purchase CTR metrics (30d)

## Phase 4: Integration

- [ ] Wire analytics scheduler into FastAPI lifespan (alongside batch loader and session expiry)
- [ ] Implement lock acquisition with 60s blocking timeout on `.batch.lock`
- [ ] Add health endpoint fields: `analytics_last_run`, `analytics_tier2_last_run`, `analytics_duration_ms`
- [ ] Add CLI trigger: `python -m app.analytics` for on-demand rebuild

## Phase 5: Testing

- [ ] Unit test each SQL query with fixture data in DuckDB
- [ ] Integration test: verify tier1 runs every cycle, tier2 only when gated
- [ ] Integration test: verify lock contention (analytics waits, event loader retries)
- [ ] Test: partial failure in one table doesn't corrupt others
- [ ] Test: compute completes in <5s for 100K events (tier1) and <60s for 1M events (tier2)
