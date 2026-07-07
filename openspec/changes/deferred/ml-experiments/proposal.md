# ML Experiments — Proposal

## Motivation

With event data flowing (Phase 2), we can experiment with ML techniques for product recommendations. This is primarily a **learning exercise** — building practical ML skills using real (small-scale) data.

If recommendations improve conversions, they stay. If they don't measurably help, that's fine — the store works great without them.

## Scope

### Capabilities

1. **Co-occurrence recommendations** — "Customers who bought X also bought Y"
2. **Popularity scoring** — Weighted blend of views, carts, and purchases
3. **Recommendation API** — `GET /v1/recommendations?product_id=X` (best-effort)
4. **Fallback chain** — ML → popularity → featured → random (never errors)
5. **Background pre-computation** — Job runs every 30 min, writes to cache

### Constraints

- Recommendations served from pre-computed cache (not computed on request)
- If cache is empty → show popular products (from SQLite order count)
- If that fails → show random active products
- ML code is never imported by Layer 1 route handlers
- The entire `app/ml/` directory can be deleted without breaking the store

## Technical Approach

- **Features:** Computed from DuckDB events (co-occurrence matrix, view counts, purchase counts)
- **Model:** Weighted linear scorer (no heavy ML frameworks needed)
- **Cache:** SQLite table (`recommendations`) or JSON file — read synchronously by API
- **Job:** APScheduler in-process, 30-minute interval
- **Dependencies:** numpy (optional, for matrix operations) — no pandas, no sklearn required

## Impact

- Potentially increases average order value through relevant suggestions
- Provides hands-on ML/data engineering learning opportunity
- Zero risk to store reliability (completely isolated from Layer 1)
