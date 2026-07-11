## ADDED Requirements

### Requirement: Accept single event via POST
The system SHALL accept a single event via `POST /v1/events` with a JSON body containing event fields.

#### Scenario: Valid single event
- **WHEN** client sends POST /v1/events with `{"session_id": "abc", "event_type": "product_view", "product_id": "SKU-1"}`
- **THEN** system returns HTTP 202 with `{"accepted": 1, "event_ids": ["<generated-uuid>"]}`

#### Scenario: Missing required field
- **WHEN** client sends POST /v1/events without `session_id`
- **THEN** system returns HTTP 422 with validation error details

#### Scenario: Invalid event_type
- **WHEN** client sends POST /v1/events with `event_type: "invalid_thing"`
- **THEN** system returns HTTP 422 indicating invalid enum value

### Requirement: Accept batch events via POST
The system SHALL accept a batch of events via `POST /v1/events` with a JSON body containing an `events` array.

#### Scenario: Valid batch of events
- **WHEN** client sends POST /v1/events with `{"events": [{"session_id": "s1", "event_type": "page_view"}, {"session_id": "s1", "event_type": "click", "product_id": "P1"}]}`
- **THEN** system returns HTTP 202 with `{"accepted": 2, "event_ids": ["<uuid1>", "<uuid2>"]}`

#### Scenario: Batch exceeds maximum size
- **WHEN** client sends POST /v1/events with more than 1000 events in the `events` array
- **THEN** system returns HTTP 422 indicating batch size exceeded

#### Scenario: Partial validation failure in batch
- **WHEN** client sends a batch where one event is invalid (e.g., missing session_id)
- **THEN** system returns HTTP 422 rejecting the entire batch (atomic validation)

### Requirement: Server-side event enrichment
The system SHALL enrich every accepted event with server-generated fields before storage.

#### Scenario: Event ID generation when omitted
- **WHEN** client sends an event without `event_id`
- **THEN** system generates a UUID4 `event_id` and includes it in the response

#### Scenario: Client-provided event ID preserved
- **WHEN** client sends an event with `event_id: "client-123"`
- **THEN** system uses "client-123" as the event_id (for idempotent retries)

#### Scenario: Server timestamp assigned
- **WHEN** client sends an event (with or without a `timestamp` field)
- **THEN** system assigns `server_timestamp` as UTC datetime at time of receipt
- **AND** if client provided `timestamp`, it is stored in `metadata.client_timestamp`

### Requirement: Event type enumeration
The system SHALL accept only valid event types from a defined set.

#### Scenario: All valid event types accepted
- **WHEN** client sends events with types: page_view, product_view, search, click, add_to_cart, remove_from_cart, purchase, impression, session_start, session_end
- **THEN** all are accepted with HTTP 202

### Requirement: Nullable user identity
The system SHALL accept events with or without a `user_id` field.

#### Scenario: Anonymous event (no user_id)
- **WHEN** client sends an event with `session_id` but no `user_id`
- **THEN** system accepts the event with `user_id` as null

#### Scenario: Identified event (with user_id)
- **WHEN** client sends an event with both `session_id: "s1"` and `user_id: "42"`
- **THEN** system accepts the event with both fields stored

### Requirement: HTTP 202 semantics
The system SHALL return HTTP 202 Accepted to indicate events are buffered but not yet queryable.

#### Scenario: Successful ingestion returns 202
- **WHEN** client sends a valid event
- **THEN** system returns HTTP 202 (not 200 or 201)
- **AND** the event is durably buffered on disk before the response is sent
