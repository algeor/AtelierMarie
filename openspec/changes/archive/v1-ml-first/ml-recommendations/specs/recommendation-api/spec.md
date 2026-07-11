## ADDED Requirements

### Requirement: GET /v1/recommendations returns personalized recommendations
The system SHALL expose `GET /v1/recommendations` that returns personalized product recommendations based on the current session and optionally the authenticated user.

The endpoint MUST read `X-Session-ID` from the request header and optionally resolve the current user via `get_current_user_optional`.

Query parameters: `n` (integer, default 10, max 50), `context_product_id` (optional, string — product being currently viewed).

#### Scenario: Recommendations for active session
- **WHEN** a GET request is made to `/v1/recommendations` with a valid `X-Session-ID` header
- **THEN** the response contains a JSON body with `recommendations` array, `strategy` string, and `cached` boolean

#### Scenario: Response format
- **WHEN** recommendations are returned successfully
- **THEN** each item in the `recommendations` array contains `product_id` (string), `score` (float 0-1), and `reason` (string enum: similar_to_viewed, frequently_bought_together, trending, session_pattern, popular, featured)

#### Scenario: Context product provided
- **WHEN** `context_product_id=SKU-1` is passed as a query parameter
- **THEN** candidates are biased toward products related to SKU-1 (co-occurrence and similar price/category)

#### Scenario: No session header
- **WHEN** the request does not include `X-Session-ID`
- **THEN** the system returns 400 Bad Request with an error message indicating the session header is required

#### Scenario: Cached response
- **WHEN** a cache entry exists for the given session (and user, if authenticated)
- **THEN** the response includes `cached: true` and is served within 200ms

### Requirement: GET /v1/recommendations/trending returns trending products
The system SHALL expose `GET /v1/recommendations/trending` that returns globally trending products based on time-decayed popularity.

This endpoint does NOT require authentication or a session header.

Query parameters: `n` (integer, default 10, max 50).

#### Scenario: Trending products returned
- **WHEN** a GET request is made to `/v1/recommendations/trending`
- **THEN** the response contains a JSON body with `recommendations` array (same format as personalized), `strategy: "trending"`, and `cached` boolean

#### Scenario: No session required
- **WHEN** the request does not include `X-Session-ID` or authentication
- **THEN** the endpoint still returns successfully with trending products

#### Scenario: Always served from cache
- **WHEN** the batch job has run at least once
- **THEN** trending recommendations are always served from cache (refreshed every 30 min)

### Requirement: Recommendation response includes strategy transparency
The system SHALL include a `strategy` field in all recommendation responses indicating which fallback level produced the results.

Valid values: `personalized`, `session_based`, `popularity`, `trending`, `featured`.

#### Scenario: Strategy reflects actual computation path
- **WHEN** the fallback chain selects session-based recommendations
- **THEN** the response `strategy` field equals "session_based"

#### Scenario: Strategy for trending endpoint
- **WHEN** the trending endpoint is called
- **THEN** the response `strategy` field always equals "trending"

### Requirement: Recommendation response indicates cache status
The system SHALL include a `cached` boolean in all recommendation responses indicating whether the result was served from precomputed cache or computed on-the-fly.

#### Scenario: Cache hit
- **WHEN** the recommendation cache has a valid (non-expired) entry for the request
- **THEN** the response contains `cached: true`

#### Scenario: Cache miss with on-the-fly computation
- **WHEN** no cache entry exists and recommendations are computed on-the-fly
- **THEN** the response contains `cached: false`
