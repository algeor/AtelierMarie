## ADDED Requirements

### Requirement: Session-based recommendations
The system SHALL expose GET /recommendations?session_id={id} that returns product recommendations based on the current session's viewed/carted products using co-occurrence similarity. Fallback SHALL be trending products when session has insufficient history.

#### Scenario: Recommendations from session history
- **WHEN** a session has viewed products A and B, and products C and D are frequently co-viewed with A and B
- **THEN** GET /recommendations returns products C and D (excluding already-viewed)

#### Scenario: Trending fallback for new sessions
- **WHEN** a session has no prior product views
- **THEN** GET /recommendations returns the top trending products (most viewed in last 7 days)

### Requirement: Similar products endpoint
The system SHALL expose GET /similar-products/{product_id} that returns products similar to the given product based on co-occurrence data (viewed-together, carted-together, purchased-together signals).

#### Scenario: Similar products returned
- **WHEN** a client sends GET /similar-products/5 and product 5 has co-occurrence data
- **THEN** the API returns up to 8 similar products sorted by similarity score

#### Scenario: No similar products available
- **WHEN** a product has no co-occurrence data (new product, no interactions)
- **THEN** the API returns products from the same category as fallback

### Requirement: Co-occurrence matrix computation
The system SHALL compute item-to-item similarity scores from three signals: products viewed together in the same session, products added to cart together, and products purchased together. Scores SHALL be weighted (purchase > cart > view).

#### Scenario: Batch recomputation
- **WHEN** the co-occurrence job runs (scheduled or triggered)
- **THEN** similarity scores are recomputed from DuckDB event data and cached

#### Scenario: Weighted scoring
- **WHEN** products A and B are purchased together 3 times and viewed together 10 times
- **THEN** the similarity score reflects purchase signal weighted higher than view signal

### Requirement: Trending products computation
The system SHALL precompute trending products as the most-viewed products in a rolling 7-day window. The cache SHALL refresh every hour.

#### Scenario: Trending products refresh
- **WHEN** 1 hour has elapsed since last computation
- **THEN** trending products are recomputed from the last 7 days of product_view events

#### Scenario: Trending products served from cache
- **WHEN** a recommendations request needs trending products
- **THEN** the precomputed cache is served without real-time DuckDB query

### Requirement: Recommendation response format
The system SHALL return recommendations as an array of objects with product_id, name, slug, price, image_url, score, and reason (e.g., "Frequently viewed together", "Trending this week").

#### Scenario: Response includes reason
- **WHEN** recommendations are generated mixing session-based and trending
- **THEN** each product includes a human-readable reason for its recommendation

### Requirement: Future-ready personalization interface
The system SHALL define interfaces for user-based personalization (after login) and model-based ranking (LightGBM, embeddings) that can be plugged in without changing the API contract. user_id SHALL never be mandatory in any recommendation endpoint.

#### Scenario: Personalization hook available
- **WHEN** a user_id is associated with the session
- **THEN** the recommendation engine can optionally incorporate user history (currently returns session-based results as default behavior)
