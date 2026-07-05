# Admin Events Log — Spec

## ADDED Requirements

### Requirement: Paginated event listing with limit and offset

GET /v1/admin/events returns a paginated list of events ordered by timestamp descending (newest first).

#### Scenario: Default pagination returns first 50 events

WHEN an admin requests GET /v1/admin/events without pagination parameters
THEN the response returns up to 50 events
AND the events are ordered by timestamp descending
AND the response includes total_count indicating the total number of matching events
AND the response includes limit=50 and offset=0

#### Scenario: Custom pagination with limit and offset

WHEN an admin requests GET /v1/admin/events?limit=20&offset=40
THEN the response returns up to 20 events starting from the 41st event (0-indexed)
AND the response includes limit=20 and offset=40
AND total_count reflects the total matching events regardless of pagination

#### Scenario: Offset beyond available data returns empty list

WHEN an admin requests GET /v1/admin/events?offset=999999
AND there are fewer than 999999 events
THEN the response returns an empty events list
AND total_count still reflects the actual total

#### Scenario: Limit capped at 100

WHEN an admin requests GET /v1/admin/events?limit=500
THEN the response uses limit=100 (maximum allowed)
AND returns up to 100 events

---

### Requirement: Filter by event_type

Events can be filtered by one or more event types using the event_type query parameter.

#### Scenario: Filter by single event type

WHEN an admin requests GET /v1/admin/events?event_type=page_view
THEN only events with event_type="page_view" are returned
AND total_count reflects only page_view events

#### Scenario: Filter by multiple event types

WHEN an admin requests GET /v1/admin/events?event_type=add_to_cart&event_type=purchase
THEN only events with event_type "add_to_cart" or "purchase" are returned

#### Scenario: Invalid event type returns empty results

WHEN an admin requests GET /v1/admin/events?event_type=nonexistent_type
THEN the response returns an empty events list with total_count=0

---

### Requirement: Filter by date range

Events can be filtered by date range using from and to query parameters in YYYY-MM-DD format.

#### Scenario: Filter by date range

WHEN an admin requests GET /v1/admin/events?from=2026-06-01&to=2026-06-30
THEN only events with timestamps between June 1, 2026 00:00:00 and June 30, 2026 23:59:59 are returned

#### Scenario: Filter with only from date

WHEN an admin requests GET /v1/admin/events?from=2026-06-15
THEN only events from June 15, 2026 onward are returned

#### Scenario: Combine event_type and date filters

WHEN an admin requests GET /v1/admin/events?event_type=purchase&from=2026-06-01&to=2026-06-30
THEN only purchase events from June 2026 are returned
AND total_count reflects only the matching subset

---

### Requirement: Event response includes full event details

Each event in the response contains all relevant fields for debugging and analysis.

#### Scenario: Event object contains required fields

WHEN an admin requests GET /v1/admin/events
THEN each event in the response contains:
- event_id (unique identifier)
- session_id (the session that generated the event)
- user_id (nullable — null for anonymous sessions)
- product_id (nullable — null for non-product events like search)
- event_type (string: page_view, product_click, add_to_cart, remove_from_cart, purchase, search)
- metadata (JSON object with event-specific data)
- timestamp (ISO 8601 format)

#### Scenario: Search event includes query in metadata

WHEN an admin requests GET /v1/admin/events?event_type=search
THEN each returned event has metadata containing at minimum: query (the search term) and result_count

#### Scenario: Add-to-cart event includes product context

WHEN an admin requests GET /v1/admin/events?event_type=add_to_cart
THEN each returned event has a non-null product_id
AND metadata contains quantity

---

### Requirement: Events ordered by timestamp descending

Events are always returned newest-first to surface recent activity immediately.

#### Scenario: Newest events appear first

WHEN an admin requests GET /v1/admin/events
AND there are events at timestamps T1 < T2 < T3
THEN the response lists events in order T3, T2, T1

#### Scenario: Pagination maintains sort order

WHEN an admin requests GET /v1/admin/events?limit=10&offset=10
THEN the returned events are still ordered by timestamp descending
AND they represent the 11th through 20th most recent events
