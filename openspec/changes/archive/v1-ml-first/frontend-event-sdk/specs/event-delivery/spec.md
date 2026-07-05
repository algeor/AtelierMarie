## ADDED Requirements

### Requirement: Event tracking API
The SDK SHALL expose a `tracker.track(eventType, data)` method that enqueues events for delivery.

#### Scenario: Track a product view
- **WHEN** `tracker.track('product_view', { product_id: 'SKU-1' })` is called
- **THEN** the SDK creates an event object with `event_id` (UUID), `event_type: 'product_view'`, `session_id` (current), `product_id: 'SKU-1'`, `timestamp` (ISO 8601), and `user_id` (if set), and adds it to the in-memory queue

#### Scenario: Track an event with metadata
- **WHEN** `tracker.track('search', { metadata: { query: 'blue shoes' } })` is called
- **THEN** the SDK creates an event with the metadata field preserved as-is in the event payload

#### Scenario: Track called when consent not granted
- **WHEN** `tracker.track()` is called and consent has not been granted (requireConsent: true)
- **THEN** the SDK returns immediately without creating or queuing any event

### Requirement: Batch flush on queue size
The SDK SHALL flush the event queue when it reaches the configured batch size.

#### Scenario: Queue reaches batch size (default 10)
- **WHEN** the 10th event is added to the queue (batchSize: 10)
- **THEN** the SDK immediately initiates a flush: splices all events from the queue and sends them via POST /v1/events

#### Scenario: Custom batch size
- **WHEN** the tracker is initialized with `{ batchSize: 5 }` and 5 events are queued
- **THEN** the SDK flushes after the 5th event

### Requirement: Batch flush on timer
The SDK SHALL flush the event queue periodically based on the configured interval.

#### Scenario: Timer fires with events in queue
- **WHEN** the flush interval elapses (default 5000ms) and the queue contains 1 or more events
- **THEN** the SDK flushes all queued events via POST /v1/events

#### Scenario: Timer fires with empty queue
- **WHEN** the flush interval elapses and the queue is empty
- **THEN** the SDK does not make any HTTP request

### Requirement: Flush on page hide
The SDK SHALL flush remaining events when the page becomes hidden (tab close, navigation, minimize).

#### Scenario: User closes tab with events in queue
- **WHEN** the `visibilitychange` event fires with `document.visibilityState === 'hidden'` and events are queued
- **THEN** the SDK flushes using `navigator.sendBeacon()` with the queued events as a JSON blob

#### Scenario: Page hidden with empty queue
- **WHEN** `visibilitychange` fires with state `hidden` and the queue is empty
- **THEN** the SDK does not call sendBeacon

### Requirement: Manual flush
The SDK SHALL expose a `tracker.flush()` method for immediate delivery.

#### Scenario: Developer triggers manual flush
- **WHEN** `tracker.flush()` is called with events in the queue
- **THEN** all queued events are sent immediately via fetch, and the method returns a Promise that resolves when delivery completes

### Requirement: Event payload format
The SDK SHALL send events as a JSON array in the expected backend format.

#### Scenario: Batch POST body structure
- **WHEN** the SDK flushes a batch of events
- **THEN** the POST body is `{ "events": [<event1>, <event2>, ...] }` with Content-Type: application/json

#### Scenario: Individual event structure
- **WHEN** an event is serialized for delivery
- **THEN** it contains at minimum: `event_id` (UUID string), `event_type` (string), `session_id` (UUID string), `timestamp` (ISO 8601 string), and optionally `user_id`, `product_id`, and `metadata` (object)

### Requirement: Identity management
The SDK SHALL expose `setUserId(id)` and `clearUserId()` methods to associate/disassociate a user with subsequent events.

#### Scenario: User logs in
- **WHEN** `tracker.setUserId('42')` is called
- **THEN** all subsequent events include `user_id: '42'` in their payload

#### Scenario: User logs out
- **WHEN** `tracker.clearUserId()` is called
- **THEN** all subsequent events have `user_id: null` (or omit the field)

### Requirement: Tracker initialization
The SDK SHALL expose an `AtelierTracker.init(config)` factory method.

#### Scenario: Initialize with required config
- **WHEN** `AtelierTracker.init({ endpoint: 'https://api.example.com' })` is called
- **THEN** the SDK returns a tracker instance configured to send events to that endpoint with default batchSize (10), flushInterval (5000ms), maxRetries (3)

#### Scenario: Initialize with custom config
- **WHEN** `AtelierTracker.init({ endpoint: '...', batchSize: 20, flushInterval: 10000, maxRetries: 5, debug: true })` is called
- **THEN** the SDK uses the provided values for all configuration options
