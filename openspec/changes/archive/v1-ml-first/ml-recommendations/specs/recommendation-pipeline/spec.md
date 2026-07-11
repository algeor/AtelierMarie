## ADDED Requirements

### Requirement: Candidate generation produces broad recall set
The system SHALL generate 50-100 candidate product_ids using multiple retrieval strategies: item co-occurrence similarity, session sequence patterns, and trending products by time-decayed popularity.

#### Scenario: Candidates from co-occurrence
- **WHEN** a session has viewed products A and B
- **THEN** candidates include products that co-occur with A or B in the features_cooccurrence table, ranked by co_count

#### Scenario: Candidates from trending
- **WHEN** the system has popularity features computed
- **THEN** candidates include the top products by popularity_score from features_item_popularity

#### Scenario: Multiple sources merged
- **WHEN** candidates are generated from all three sources
- **THEN** the union of candidates is deduplicated and capped at ~100 product_ids

### Requirement: Ranking scores candidates with weighted linear combination
The system SHALL score each candidate using a configurable weighted linear combination of: CTR score, popularity score, category diversity penalty, and price range relevance.

Weights MUST be configurable via pydantic-settings (environment variables or config file).

#### Scenario: Ranking with default weights
- **WHEN** candidates are scored with default weights (ctr=0.3, popularity=0.3, diversity=0.2, price_relevance=0.2)
- **THEN** each candidate receives a final score between 0.0 and 1.0 computed as the weighted sum of normalized component scores

#### Scenario: Category diversity penalty
- **WHEN** multiple candidates share the same category
- **THEN** subsequent items from the same category receive a decreasing diversity score (first=1.0, second=0.5, third=0.25, etc.)

#### Scenario: Price range relevance
- **WHEN** a session has viewed products in the $20-$50 range
- **THEN** candidates in a similar price range receive higher price_relevance scores than those far outside the range

### Requirement: Filtering removes ineligible products
The system SHALL filter ranked candidates by removing: products already viewed in the current session, inactive products (is_active=FALSE), and excess items from any single category (max 3 per category).

#### Scenario: Already-viewed products removed
- **WHEN** a user has viewed product A in the current session
- **THEN** product A does NOT appear in the final recommendations

#### Scenario: Inactive products removed
- **WHEN** a product has is_active=FALSE in the product catalog
- **THEN** that product does NOT appear in the final recommendations

#### Scenario: Category cap enforced
- **WHEN** 5 candidates from category "Electronics" survive ranking
- **THEN** only the top 3 by score appear in the final output

### Requirement: Fallback chain handles cold start
The system SHALL implement a four-level fallback chain for recommendation generation:
1. Personalized (user has ≥20 events across sessions)
2. Session-based (current session has ≥3 product interactions)
3. Popularity-based (system has ≥1000 total events)
4. Featured products (manual curation, always available)

The system MUST always return results by falling through levels until one succeeds.

#### Scenario: Personalized recommendations for active user
- **WHEN** a logged-in user has 25 historical events and requests recommendations
- **THEN** the system uses Level 1 (personalized) with strategy="personalized"

#### Scenario: Session-based for anonymous user with activity
- **WHEN** an anonymous session has 5 product interactions
- **THEN** the system uses Level 2 (session-based) with strategy="session_based"

#### Scenario: Popularity-based for new session
- **WHEN** a new session with 0 interactions requests recommendations and the system has >1000 events
- **THEN** the system uses Level 3 (popularity) with strategy="popularity"

#### Scenario: Featured products on day one
- **WHEN** the system has <1000 total events and the session has no interactions
- **THEN** the system uses Level 4 (featured) with strategy="featured"

#### Scenario: Fallback always returns results
- **WHEN** any request is made for recommendations with n=10
- **THEN** the system returns between 1 and n products (never an empty list, assuming at least one featured product exists)

### Requirement: Top-N output with configurable count
The system SHALL return the top-N recommendations (default N=10) after all pipeline stages complete.

#### Scenario: Default count
- **WHEN** a request for recommendations does not specify a count
- **THEN** the system returns up to 10 recommendations

#### Scenario: Custom count
- **WHEN** a request specifies n=5
- **THEN** the system returns up to 5 recommendations

#### Scenario: Fewer products available than requested
- **WHEN** a request specifies n=10 but only 3 eligible products exist
- **THEN** the system returns 3 recommendations (no padding with duplicates)
