# funnel-analytics Specification

## Purpose
TBD - created by archiving change first-party-funnel-analytics. Update Purpose after archive.
## Requirements
### Requirement: First-party funnel event taxonomy
The system SHALL define a first-party funnel event taxonomy containing exactly these initial behavioral event types: `product_view`, `listing_filter`, `add_to_cart`, `cart_open`, `checkout_start`, `delivery_selected`, `shipping_quote_selected`, `order_submit`, `payment_redirect`, and `purchase_confirmed`.

Each accepted event SHALL include `event_id`, `event_type`, `occurred_at`, server-derived `session_id`, optional authenticated `user_id`, active locale, page path when available, and event-specific properties from an allowlist. Event payloads MUST NOT include customer email, phone, name, delivery address, customer notes, raw IP address, payment card data, or arbitrary free-form text.

#### Scenario: Product view event shape
- **WHEN** a consented visitor opens a product detail page
- **THEN** the frontend emits `product_view` with `product_id`, active locale, page path, and a unique `event_id`
- **AND** the backend persists the event with the server-derived session ID

#### Scenario: Checkout funnel event shape
- **WHEN** a consented visitor starts checkout, selects delivery, submits an order, and is redirected to payment
- **THEN** the emitted events use `checkout_start`, `delivery_selected`, `order_submit`, and `payment_redirect`
- **AND** event properties include only allowed values such as delivery method, courier, order ID, payment method, value cents, and currency

#### Scenario: Shipping quote event waits for selectable quotes
- **WHEN** the checkout flow does not yet expose selectable shipping quotes
- **THEN** no `shipping_quote_selected` event is emitted
- **AND** the event remains reserved for the `shipping-pricing` flow once quote selection exists

#### Scenario: PII payload rejected
- **WHEN** an event payload includes email, phone, delivery address, customer name, or unknown metadata keys
- **THEN** the ingestion API rejects the event with HTTP 422 and does not persist it

### Requirement: Consent-gated frontend event emission
The frontend SHALL emit behavioral analytics events only when analytics consent is granted. If analytics consent is missing or rejected, the frontend SHALL NOT send product, listing, cart, checkout, delivery, payment, or purchase analytics events.

#### Scenario: No consent prevents events
- **WHEN** a visitor has not made a cookie choice and views a product
- **THEN** no `product_view` analytics request is sent

#### Scenario: Rejected analytics prevents events
- **WHEN** a visitor selected necessary cookies only and adds a product to cart
- **THEN** no `add_to_cart` analytics request is sent

#### Scenario: Accepted analytics sends events
- **WHEN** a visitor accepted analytics cookies and opens the cart drawer
- **THEN** the frontend sends a `cart_open` event to the analytics ingestion endpoint

### Requirement: Analytics ingestion API
The system SHALL expose a public `POST /v1/analytics/events` endpoint that accepts one event or a bounded batch of events from the current session. The endpoint SHALL validate event type, event ID format, occurred timestamp, property allowlist, payload size, and batch size before accepting the events.

Accepted events SHALL return HTTP 202. Invalid events SHALL return HTTP 422. Analytics ingestion failures SHALL NOT affect cart, checkout, payment, or order APIs.

#### Scenario: Single event accepted
- **WHEN** a consented client sends one valid `add_to_cart` event
- **THEN** the endpoint returns HTTP 202 and appends the event to analytics storage

#### Scenario: Batch accepted
- **WHEN** a consented client sends a valid batch of funnel events within the configured batch limit
- **THEN** the endpoint returns HTTP 202 and appends all events to analytics storage

#### Scenario: Oversized batch rejected
- **WHEN** a client sends more events than the configured batch limit
- **THEN** the endpoint returns HTTP 422 and does not persist the oversized batch

### Requirement: Idempotent event delivery
The analytics ingestion service SHALL treat `event_id` as an idempotency key. If the same session sends the same `event_id` more than once, the system SHALL store only one accepted event and SHALL count the duplicate for delivery health reporting.

#### Scenario: Duplicate event is not double-counted
- **WHEN** the same `event_id` is delivered twice because of a retry
- **THEN** analytics storage contains only one event row for that event ID and session

### Requirement: JSONL and DuckDB analytics storage
The system SHALL persist accepted analytics events to append-only JSONL as the durable source of truth and load accepted events into DuckDB tables for aggregate reporting. DuckDB tables SHALL be rebuildable from JSONL without losing accepted events.

#### Scenario: Accepted event written durably
- **WHEN** the ingestion API accepts a `product_view` event
- **THEN** the event is appended to the JSONL event log
- **AND** the event becomes queryable through DuckDB after flush/load completes

#### Scenario: DuckDB rebuild preserves counts
- **WHEN** the DuckDB analytics database is rebuilt from JSONL
- **THEN** event counts by event type match the JSONL source for the same date range

### Requirement: Backend purchase confirmation source
The final purchase metric SHALL be reconciled with backend order state. `purchase_confirmed` SHALL be recorded when the backend successfully creates an order, for every payment method. Failed checkout/order attempts SHALL NOT create `purchase_confirmed`.

#### Scenario: Order creation creates purchase confirmation
- **WHEN** a consented visitor completes checkout and the backend successfully creates an order
- **THEN** a `purchase_confirmed` event is recorded with order ID, value cents, currency, and payment method

#### Scenario: Card order purchase confirmation precedes payment redirect
- **WHEN** a consented visitor completes checkout with card payment and the backend creates the order
- **THEN** a `purchase_confirmed` event is recorded for the created order
- **AND** a separate `payment_redirect` event may be recorded when the visitor is sent to Stripe

#### Scenario: Failed order does not create purchase confirmation
- **WHEN** order submission fails because the cart is empty, stock is insufficient, or delivery validation fails
- **THEN** no `purchase_confirmed` event is recorded

### Requirement: Checkout-time analytics consent snapshot
The system SHALL capture whether analytics consent was granted at checkout time for every created order, using either an order column or an equivalent consent ledger keyed by order/session. Order-created `purchase_confirmed` events SHALL be recorded only when this snapshot shows analytics consent was granted.

#### Scenario: Order without consent does not create analytics purchase
- **WHEN** an order is created without analytics consent
- **THEN** no `purchase_confirmed` analytics event is recorded

#### Scenario: Order with consent creates analytics purchase
- **WHEN** an order is created with analytics consent
- **THEN** a `purchase_confirmed` analytics event is recorded using the stored consent snapshot

### Requirement: Analytics erasure and retention coverage
Analytics events SHALL participate in the GDPR erasure and retention model. When a data-subject erasure operation resolves a subject by `user_id`, email-linked order, or session ID, matching analytics events SHALL be deleted or irreversibly anonymized according to the chosen retention policy.

#### Scenario: Erasure removes linked analytics identity
- **WHEN** an admin erases a data subject whose orders or sessions are linked to analytics events
- **THEN** those analytics events no longer contain the subject's session ID, user ID, order ID, or other linkable identifiers after erasure completes

### Requirement: Event delivery health measurement
The system SHALL expose delivery-health metrics including accepted event count, rejected event count, duplicate event count, validation failure count, last successful flush time, and DuckDB load status.

#### Scenario: Admin sees delivery health
- **WHEN** an admin requests analytics health for the last 24 hours
- **THEN** the response includes accepted, rejected, duplicate, validation failure, and flush status metrics

