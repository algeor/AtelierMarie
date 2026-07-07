# ML Experiments — Design

## Architecture

```
DuckDB (analytics.db)                    SQLite (atelier.db)
├── events                               ├── products (is_active, stock)
└── session_identity                     └── recommendations (cache)
        │                                        ▲
        │  Background job (every 30 min)         │ writes
        ▼                                        │
┌─────────────────────────────────────────────────┐
│  ML Pipeline (app/ml/)                           │
│                                                  │
│  1. Read events from DuckDB (last 30 days)       │
│  2. Compute co-occurrence matrix                 │
│  3. Compute popularity scores                    │
│  4. Rank candidates per product                  │
│  5. Write top-N recommendations to cache         │
└──────────────────────────────────────────────────┘
        │
        │  API reads from cache (synchronous)
        ▼
┌─────────────────────────────────────────┐
│  GET /v1/recommendations?product_id=X    │
│                                          │
│  Fallback chain:                         │
│  1. Cached ML recommendations            │
│  2. Popular products (by order count)    │
│  3. Featured products (is_featured=1)    │
│  4. Random active products               │
└──────────────────────────────────────────┘
```

## Recommendation Cache Schema (SQLite)

```sql
-- Lives in atelier.db alongside other tables
-- This is the ONLY thing Layer 1 reads from ML
CREATE TABLE recommendations (
    product_id      TEXT NOT NULL,
    recommended_id  TEXT NOT NULL,
    score           REAL NOT NULL,
    strategy        TEXT NOT NULL,    -- 'cooccurrence' | 'popularity'
    rank            INTEGER NOT NULL,
    computed_at     TEXT NOT NULL,
    PRIMARY KEY (product_id, recommended_id)
);

CREATE INDEX idx_reco_product ON recommendations(product_id, rank);
```

## Co-occurrence Algorithm

```python
# Simplified: for each pair of products bought in the same order,
# increment their co-occurrence count

def compute_cooccurrence(events):
    """
    SELECT oi1.product_id, oi2.product_id, COUNT(*) as co_count
    FROM events e1
    JOIN events e2 ON e1.session_id = e2.session_id
    WHERE e1.event_type = 'purchase' AND e2.event_type = 'purchase'
      AND e1.product_id != e2.product_id
      AND e1.timestamp > now() - INTERVAL 30 DAY
    GROUP BY 1, 2
    ORDER BY co_count DESC
    """
    # Returns: {product_id: [(other_product_id, score), ...]}
```

## Popularity Algorithm

```python
def compute_popularity(events):
    """
    Weighted score:
    - 1 point per page_view
    - 3 points per add_to_cart
    - 10 points per purchase
    - Recency boost: events in last 7 days weighted 2x

    Returns: [(product_id, score), ...] sorted descending
    """
```

## Fallback Chain (in recommendation route handler)

```python
async def get_recommendations(product_id: str, limit: int = 4):
    # 1. Try ML cache
    recs = db.execute(
        "SELECT recommended_id FROM recommendations WHERE product_id=? ORDER BY rank LIMIT ?",
        (product_id, limit)
    ).fetchall()
    if recs:
        return load_products([r.recommended_id for r in recs])

    # 2. Try popularity (from SQLite - count of order_items)
    popular = db.execute(
        "SELECT product_id, COUNT(*) as cnt FROM order_items GROUP BY 1 ORDER BY cnt DESC LIMIT ?",
        (limit,)
    ).fetchall()
    if popular:
        return load_products([p.product_id for p in popular if p.product_id != product_id])

    # 3. Try featured
    featured = db.execute(
        "SELECT id FROM products WHERE is_featured=1 AND is_active=1 AND id!=? LIMIT ?",
        (product_id, limit)
    ).fetchall()
    if featured:
        return load_products([f.id for f in featured])

    # 4. Random
    return db.execute(
        "SELECT id FROM products WHERE is_active=1 AND id!=? ORDER BY RANDOM() LIMIT ?",
        (product_id, limit)
    ).fetchall()
```

## Background Job

- **Schedule:** Every 30 minutes (APScheduler)
- **Duration:** Should complete in <30 seconds (at <10K events)
- **Process:** Read from DuckDB → compute → write to SQLite recommendations table
- **Failure:** Log error, continue. Stale recommendations are acceptable.
- **First run:** If no events exist yet, job completes instantly (nothing to compute)

## API

```
GET /v1/recommendations?product_id={id}&limit=4

Response:
{
  "recommendations": [
    {"id": "...", "name": "...", "price_cents": 2400, "image_url": "..."},
    ...
  ],
  "strategy": "cooccurrence" | "popularity" | "featured" | "random"
}
```

The `strategy` field tells the frontend (and analytics) which fallback level was used.
