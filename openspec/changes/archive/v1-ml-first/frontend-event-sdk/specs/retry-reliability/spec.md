## ADDED Requirements

### Requirement: Client-generated event_id for idempotency
The SDK SHALL assign a unique `event_id` (UUID v4 via crypto.randomUUID()) to every event at track() time, before the event enters the queue.

#### Scenario: Event created with pre-assigned ID
- **WHEN** `tracker.track('product_view', { product_id: 'SKU-1' })` is called
- **THEN** the event object immediately receives an `event_id` field containing a UUID v4 string, and this ID persists through all retry attempts

#### Scenario: Same event_id on retry
- **WHEN** a batch delivery fails and the SDK retries
- **THEN** the retried events carry the same `event_id` values as the original attempt (enabling server-side INSERT OR IGNORE dedup)

### Requirement: Exponential backoff retry on failure
The SDK SHALL retry failed deliveries up to maxRetries times with exponential backoff.

#### Scenario: First retry after 5xx response
- **WHEN** a fetch to POST /v1/events returns a 5xx status code
- **THEN** the SDK waits 1000ms and retries with the same batch payload

#### Scenario: Second retry
- **WHEN** the first retry also fails with 5xx
- **THEN** the SDK waits 2000ms and retries again

#### Scenario: Third and final retry
- **WHEN** the second retry also fails
- **THEN** the SDK waits 4000ms and retries one last time (attempt 3 of 3)

#### Scenario: All retries exhausted
- **WHEN** the third retry also fails
- **THEN** the SDK drops the batch (events are lost) and logs a warning if debug mode is enabled

#### Scenario: 429 Too Many Requests
- **WHEN** the server responds with HTTP 429
- **THEN** the SDK applies the same exponential backoff retry strategy as 5xx errors

### Requirement: Successful delivery clears queue
The SDK SHALL remove events from the retry pipeline on successful delivery.

#### Scenario: 202 Accepted response
- **WHEN** a fetch to POST /v1/events returns HTTP 202
- **THEN** the SDK considers those events delivered and does not retry them

#### Scenario: 4xx client error (not 429)
- **WHEN** a fetch returns HTTP 400 or 422
- **THEN** the SDK does NOT retry (client error indicates bad payload, not transient failure) and drops the batch

### Requirement: sendBeacon for page unload delivery
The SDK SHALL use navigator.sendBeacon() for event delivery when the page is being unloaded, as fetch() is cancelled during page teardown.

#### Scenario: Tab close with pending events
- **WHEN** visibilitychange fires with state 'hidden' and there are events in the queue
- **THEN** the SDK calls `navigator.sendBeacon(endpoint + '/v1/events', blob)` where blob is a JSON Blob with Content-Type application/json

#### Scenario: sendBeacon returns false (browser rejected)
- **WHEN** sendBeacon returns false (payload too large or browser limit reached)
- **THEN** the events are lost (no retry possible during unload) — acceptable degradation

### Requirement: No concurrent duplicate flushes
The SDK SHALL prevent multiple simultaneous flush operations for the same events.

#### Scenario: Timer fires during an in-flight flush
- **WHEN** a flush is already in progress (fetch pending) and the timer fires again
- **THEN** the SDK only flushes NEW events added since the in-flight flush started, not the ones already in transit
