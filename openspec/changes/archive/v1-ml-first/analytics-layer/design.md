# Analytics Layer — Design

## Context

AtelierMarie captures behavioral events into DuckDB via a JSONL buffer + batch loader. Multiple services need aggregated views of this data:
- ML recommendations needs popularity scores, co-occurrence patterns, CTR metrics
- Admin dashboard needs product metrics, session breakdowns, conversion funnels, search analytics
- Storefront could use "trending" signals for product badges

Currently these consumers would independently query the same events table with overlapping logic. The analytics layer centralizes this computation.

## Goals

- Single compute path for all event-derived aggregates
- Tiered refresh: cheap metrics every 5 min, expensive ML features every 30 min
- SQL-as-files for auditability and independent testing
- Eliminate `.ml-compute.lock` — unify on single `.batch.lock`
- Consumers become pure readers of pre-materialized tables

## Non-Goals

- Point-in-time feature snapshots (no history needed)
- Real-time aggregates (5-min staleness is acceptable)
- External tooling or infrastructure
- Custom date-range pre-computation (admin falls through to direct query)

## Decisions

### 1. Two-tier refresh schedule

**Choice:** Single job runs every 5 minutes. Tier 1 (cheap aggregates) rebuilds every run. Tier 2 (expensive ML features) rebuilds only when ≥30 minutes have elapsed since last Tier 2 run.

**Alternatives considered:**
- Two separate jobs: adds coordination complexity for no benefit
- Single 30-min refresh for everything: admin dashboard would be too stale
- Single 5-min refresh for everything: co-occurrence self-join too expensive at high frequency

**Rationale:** Tier 1 queries are simple COUNT/SUM/GROUP BY (~2s for 1M events). Tier 2 involves self-joins and windowed sequences (~30s for 1M events). Splitting tiers gives fresh dashboard metrics without paying the co-occurrence cost every 5 minutes.

### 2. SQL-as-files pattern

**Choice:** Each analytics table is defined by a `.sql` file in `app/analytics/queries/`. The compute job reads and executes these files in dependency order.

**Alternatives considered:**
- SQL embedded in Python: harder to audit, harder to test independently
- ORM/query builder: DuckDB SQL is already expressive enough, no abstraction needed

**Rationale:** SQL files are independently testable (`duckdb < query.sql`), auditable in code review, and can be profiled/explained without running Python. The compute orchestrator is just: read file → execute → log stats.

### 3. Single `.batch.lock` for all DuckDB writers

**Choice:** Eliminate `.ml-compute.lock`. All DuckDB write operations (event loader, session flush, analytics compute) share `.batch.lock` with different contention strategies:
- Event loader: non-blocking try, retry in 1s
- Session flush: non-blocking try, skip cycle if held
- Analytics compute: blocking wait with 60s timeout

**Alternatives considered:**
- Keep separate locks: DuckDB is single-writer per file, so separate locks create false concurrency impression
- Reader-writer lock: unnecessary complexity for the access pattern

**Rationale:** DuckDB physically cannot have concurrent writers. One lock reflects this truth. Different wait strategies match each job's urgency: event loader retries quickly (data arriving), session flush is deferrable, analytics compute is the longest-running and least urgent.

### 4. `analytics_` table prefix namespace

**Choice:** All materialized tables use `analytics_` prefix (e.g., `analytics_product_metrics`, `analytics_cooccurrence`).

**Rationale:** Clear separation from raw tables (`events`, `session_identity`). Any developer can `SHOW TABLES` and immediately see what's computed vs raw. Prevents accidental coupling to table internals.

### 5. DROP + CREATE AS SELECT (full rebuild)

**Choice:** Every tier rebuild drops and recreates tables. No incremental updates.

**Rationale:** Same reasoning as original ML design — full rebuild avoids incremental state bugs. DuckDB handles <10M events in seconds for these queries. At the scale where incremental matters (>100M events), the entire architecture would need rethinking anyway.

### 6. Analytics job runs inside API process lifespan

**Choice:** The analytics compute job runs as a background task within the FastAPI lifespan (same as event batch loader and session expiry). No separate systemd service needed.

**Alternatives considered:**
- Separate systemd service: adds ops complexity for a 2-30s periodic task
- Cron job: less observable, no graceful shutdown

**Rationale:** The job is lightweight and periodic. Running inside the API process means it participates in graceful shutdown, shares the DuckDB connection, and is observable via the health endpoint. The existing pattern (batch loader as background task) already proves this works.

## Table Schemas

### Tier 1 (5-minute refresh)

**`analytics_product_metrics`**
```sql
product_id VARCHAR,
view_count INTEGER,
cart_count INTEGER,
purchase_count INTEGER,
unique_sessions INTEGER,
revenue DECIMAL(10,2),
-- Computed over last 30 days
```

**`analytics_session_metrics`**
```sql
-- Single-row summary table
total_sessions INTEGER,
anonymous_sessions INTEGER,
authenticated_sessions INTEGER,
converted_sessions INTEGER,
avg_events_per_session DECIMAL(6,2),
-- Computed over last 30 days
```

**`analytics_search_terms`**
```sql
query VARCHAR,
search_count INTEGER,
avg_result_count DECIMAL(6,2),
-- Normalized (lowercased), last 30 days
```

**`analytics_funnel`**
```sql
-- Single-row summary table
total_views INTEGER,
total_carts INTEGER,
total_checkouts INTEGER,
total_purchases INTEGER,
conversion_rate DECIMAL(6,4),
cart_rate DECIMAL(6,4),
total_revenue DECIMAL(12,2),
-- Computed over last 30 days
```

### Tier 2 (30-minute refresh)

**`analytics_popularity`**
```sql
product_id VARCHAR,
popularity_score DECIMAL(10,2),
view_count INTEGER,
cart_count INTEGER,
purchase_count INTEGER,
unique_sessions INTEGER,
recency_boost DECIMAL(6,2),  -- 2x weight for last 7 days
-- Last 30 days with time-decay
```

**`analytics_cooccurrence`**
```sql
product_a VARCHAR,
product_b VARCHAR,
co_count INTEGER,
-- product_a < product_b, co_count >= 2, last 30 days
```

**`analytics_session_sequences`**
```sql
session_id VARCHAR,
product_sequence VARCHAR[],   -- ordered by timestamp
event_sequence VARCHAR[],
-- Last 7 days only
```

**`analytics_ctr`**
```sql
product_id VARCHAR,
impressions INTEGER,
clicks INTEGER,
purchases INTEGER,
ctr DECIMAL(6,4),
conversion_rate DECIMAL(6,4),
-- Last 30 days
```

## Compute Flow

```
analytics_compute() called every 5 minutes:
│
├── acquire .batch.lock (blocking, 60s timeout)
│
├── TIER 1 (always):
│   ├── DROP + CREATE analytics_product_metrics
│   ├── DROP + CREATE analytics_session_metrics
│   ├── DROP + CREATE analytics_search_terms
│   └── DROP + CREATE analytics_funnel
│
├── if time_since_last_tier2 >= 30 min:
│   ├── DROP + CREATE analytics_popularity
│   ├── DROP + CREATE analytics_cooccurrence
│   ├── DROP + CREATE analytics_session_sequences
│   └── DROP + CREATE analytics_ctr
│
├── release .batch.lock
│
└── log stats (duration, rows per table, tier2_ran: bool)
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Analytics job holds lock for 2-30s, blocking event loader | Event loader retries in 1s; 30s max hold is rare (only during tier2). Events buffer safely in JSONL during lock hold. |
| Table DROP + CREATE causes brief read inconsistency | DuckDB transactions: wrap each table rebuild in a transaction. Readers see old data until commit. |
| Analytics job fails mid-rebuild (partial state) | Each table rebuilt independently. Partial failure leaves some tables stale but not corrupted. Log + alert on failure. |
| Tier 1 takes >5 min at scale | Monitor compute duration. If approaching threshold, add time-bounded WHERE clauses or partition events table. |
| Adding new analytics table requires job restart | SQL-as-files: add new .sql file, job picks it up on next run. No restart needed if using file discovery. |

## Open Questions

None — design is self-contained given existing architecture constraints.
