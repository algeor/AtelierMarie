# Analytics Sandbox — Tasks

## DuckDB + JSONL Setup (Day 1 of Phase 2)

- [ ] Add `duckdb` to project dependencies
- [ ] Create `app/analytics/__init__.py` (public API: `collect()`, `init()`, `shutdown()`)
- [ ] Create `app/analytics/database.py` (DuckDB connection, schema init)
- [ ] Create `app/analytics/writer.py` (JSONL append writer, O_APPEND, date-partitioned files)
- [ ] Create DuckDB schema (events + session_identity tables)
- [ ] Create `data/events/` directory structure
- [ ] Add `ANALYTICS_ENABLED` config flag + all analytics config vars
- [ ] Integrate with app lifespan (init on startup, shutdown flush on exit)

## Batch Loader (Day 2)

- [ ] Create `app/analytics/loader.py` (background thread: read JSONL → INSERT OR IGNORE → archive)
- [ ] Handle today's file (re-readable, dedup via event_id PK)
- [ ] Handle yesterday+ files (load → move to archive/)
- [ ] Ignore corrupt lines (log warning, continue)
- [ ] Start loader thread only from worker 0 (or as lifespan singleton)
- [ ] Write tests (create JSONL, run loader, verify DuckDB rows, verify dedup)

## Event Endpoint + Models (Day 3)

- [ ] Create `app/models/events.py` (EventType enum, EventCreate schema, EventBatch request)
- [ ] Create `app/routes/events.py` (POST /v1/events — 202 Accepted, writes to JSONL)
- [ ] Validate event_type against enum (reject unknown types)
- [ ] Generate event_id server-side if client doesn't provide one
- [ ] Stamp `received_at` server-side
- [ ] When `ANALYTICS_ENABLED=false` → accept request, drop silently (still 202)
- [ ] Write tests (valid batch, invalid type, disabled mode)

## Instrument Backend Routes (Day 4)

- [ ] Create `app/analytics/collect.py` (helper: `collect(event)` → writes JSONL, safe if disabled)
- [ ] Emit `add_to_cart` event from cart add route (via BackgroundTasks)
- [ ] Emit `remove_from_cart` event from cart remove route
- [ ] Emit `purchase` event from checkout route
- [ ] Emit `search` event from product search route
- [ ] Emit `_session_link` event on OAuth login (for session_identity)
- [ ] Verify: disable analytics → all Layer 1 routes work identically (no import errors, no slowdown)

## Frontend Tracking (Day 5)

- [ ] Create `frontend/lib/analytics.ts` (~20 lines: buffer + flush + sendBeacon)
- [ ] Track `page_view` on product detail page mount
- [ ] Flush buffer on `visibilitychange` (tab close/switch)
- [ ] Verify: events appear in JSONL files after browsing
- [ ] Verify: sendBeacon works on tab close (check network tab)

## Admin Analytics Dashboard (Days 6-7)

- [ ] Create `app/analytics/queries.py` (revenue_by_day, top_products, conversion_funnel, search_terms, daily_sessions)
- [ ] Add analytics routes to `app/routes/admin.py` (GET /v1/admin/analytics)
- [ ] Frontend: admin analytics page (tables/numbers — no charting library needed for MVP)
- [ ] Write tests for analytics queries (seed JSONL, run loader, query DuckDB, verify)

## Hardening + Rebuild (Day 8)

- [ ] Create `app/analytics/rebuild.py` (CLI: replay all JSONL into fresh DuckDB)
- [ ] JSONL archive rotation (gzip files older than current day, delete after 30 days)
- [ ] Verify graceful degradation: delete analytics.db → store works, loader recreates it
- [ ] Verify no disk leak: archive rotation actually cleans up old files
- [ ] Add disk usage check to admin dashboard (data/ directory size)
- [ ] Load test: write 1000 events rapidly → verify no impact on product page latency

---

**Total: ~30 tasks, 2 weeks, 1 developer.**
