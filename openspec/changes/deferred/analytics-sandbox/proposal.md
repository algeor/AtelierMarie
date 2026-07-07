# Analytics Sandbox — Proposal

## Motivation

Once the store is live and selling, we want to understand customer behavior: what products are popular, where people drop off, what searches lead nowhere. This data also feeds future ML experiments.

**This is Layer 2.** It must never affect the store's reliability or performance.

## Scope

### Capabilities

1. **Event Collection** — Fire-and-forget API for tracking page views, cart actions, purchases, searches
2. **DuckDB Storage** — Append-only event log for analytical queries
3. **Admin Analytics** — Dashboard showing business metrics (revenue trends, top products, conversion funnel)
4. **Session Identity** — Link anonymous session events to authenticated users (at query time, not by mutation)

### Constraints

- Event ingestion adds <5ms to response time (queued after response sent)
- Analytics queries are admin-only (never user-facing)
- If DuckDB is deleted, the store continues working perfectly
- Can be completely disabled via `ANALYTICS_ENABLED=false` env var

## Technical Approach

- **Storage:** DuckDB (embedded columnar database, single file)
- **Ingestion:** In-memory asyncio.Queue → background thread flushes to DuckDB every 60s
- **Identity:** `session_identity` table populated on login, JOINed at query time
- **No JSONL buffer.** At expected scale (<1000 events/day), in-memory queue is sufficient.

## Impact

- Provides visibility into customer behavior
- Enables data-driven product decisions
- Creates the data foundation for Phase 3 (ML experiments)
- Zero impact on Layer 1 performance or reliability
