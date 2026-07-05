# ML Experiments — Tasks

## No fixed schedule. Work on these when Phase 2 is collecting data.

### Foundation

- [ ] Create `app/ml/__init__.py`
- [ ] Create `app/ml/features.py` (read events from DuckDB, compute co-occurrence + popularity)
- [ ] Create `recommendations` table in SQLite schema
- [ ] Write tests for feature computation (seed DuckDB with test events)

### Recommendation Engine

- [ ] Create `app/ml/recommender.py` (compute recommendations, write to cache)
- [ ] Implement co-occurrence algorithm
- [ ] Implement popularity scoring algorithm
- [ ] Implement fallback chain (ML → popularity → featured → random)
- [ ] Write tests for fallback behavior (empty cache, partial cache)

### API + Job

- [ ] Create `app/routes/recommendations.py` (GET /v1/recommendations)
- [ ] Create `app/ml/jobs.py` (APScheduler job, 30-min interval)
- [ ] Integrate job with app lifespan (start on startup, stop on shutdown)
- [ ] Write integration test (seed events → run job → verify API returns recommendations)

### Frontend Integration

- [ ] Add "You might also like" section to product detail page
- [ ] Show `strategy` badge for debugging (dev mode only)
- [ ] Handle empty recommendations gracefully (hide section)

### Measurement (Optional)

- [ ] Track `recommendation_click` event (which product, which strategy)
- [ ] Compare conversion rates: with vs without recommendations
- [ ] Dashboard: recommendation coverage (% of products with ML recs)

---

**Total: ~15 tasks. No deadline — this is a learning sandbox.**
