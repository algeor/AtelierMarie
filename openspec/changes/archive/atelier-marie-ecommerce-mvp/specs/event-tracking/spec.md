## ADDED Requirements

### Requirement: Client-side event emission
The frontend SHALL emit events for: session_start, product_view, impression, click_product, search_query, add_to_cart, remove_from_cart, purchase, newsletter_signup, and contact_submit. Every event SHALL include session_id. user_id SHALL be included when the user is authenticated.

#### Scenario: Product view event emitted
- **WHEN** a user navigates to a product detail page
- **THEN** a product_view event is emitted with session_id, product_id, and timestamp

#### Scenario: Add to cart event emitted
- **WHEN** a user adds a product to cart
- **THEN** an add_to_cart event is emitted with session_id, product_id, quantity, and timestamp

#### Scenario: Events include user_id after login
- **WHEN** an authenticated user views a product
- **THEN** the event includes both session_id and user_id

### Requirement: Event ingestion API
The system SHALL expose POST /events accepting a single event or batch of events. Each event SHALL include event_type, session_id, optional user_id, optional product_id, optional metadata (JSON), and timestamp. Events SHALL be written to DuckDB.

#### Scenario: Single event ingestion
- **WHEN** a client sends POST /events with a valid event payload
- **THEN** the event is persisted to DuckDB and HTTP 202 is returned

#### Scenario: Batch event ingestion
- **WHEN** a client sends POST /events with an array of 5 events
- **THEN** all 5 events are persisted and HTTP 202 is returned

#### Scenario: Invalid event rejected
- **WHEN** a client sends POST /events without required session_id
- **THEN** the API returns HTTP 422 with validation error

### Requirement: Event write buffering
The system SHALL buffer incoming events and flush to DuckDB in batches (every 5 seconds or every 100 events, whichever comes first) to avoid per-request write overhead.

#### Scenario: Buffer flushes on count threshold
- **WHEN** 100 events accumulate in the buffer
- **THEN** all 100 events are flushed to DuckDB in a single batch write

#### Scenario: Buffer flushes on time threshold
- **WHEN** 5 seconds elapse with 30 events in the buffer
- **THEN** the 30 events are flushed to DuckDB

### Requirement: Session start tracking
The system SHALL automatically emit a session_start event when a new session_id is generated (first visit). The event SHALL include user agent and referrer metadata.

#### Scenario: New session triggers event
- **WHEN** a new visitor loads the site and receives a fresh session_id
- **THEN** a session_start event is emitted with user_agent and referrer in metadata

### Requirement: Impression tracking for product grid
The system SHALL track product impressions when product cards enter the viewport (using IntersectionObserver). Each impression SHALL record the product_id and position in the grid.

#### Scenario: Product card enters viewport
- **WHEN** a product card scrolls into the visible viewport for at least 1 second
- **THEN** an impression event is emitted with product_id and grid position in metadata

### Requirement: Search query tracking
The system SHALL emit a search_query event when a user submits or pauses typing in the search overlay. The event SHALL include the query text and result count.

#### Scenario: Search query tracked
- **WHEN** a user types "vanilla" in search and results appear
- **THEN** a search_query event is emitted with query "vanilla" and result_count in metadata
