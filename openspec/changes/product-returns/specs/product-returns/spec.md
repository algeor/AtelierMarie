## ADDED Requirements

### Requirement: Request a return for delivered items
The system SHALL expose `POST /v1/orders/{id}/returns` allowing the owning session or
user to request a return against a `delivered` order. The request SHALL specify one or
more order line items with quantities and a `reason_code` (one of `damaged`,
`wrong_item`, `not_as_described`, `changed_mind`, `other`) plus optional sanitized
`reason_text`. On success the API creates a `returns` row in status `requested` with
its `return_items`, records a `requested` event, queues the `admin_return_requested`
email, and returns the created return with a computed `refund_amount_cents`.

#### Scenario: Customer requests a partial return on a delivered order
- **WHEN** the owning session requests a return of 1 of 2 units of an order item on a delivered order within the return window
- **THEN** a return is created with status `requested`, one return_item with quantity 1, `refund_amount_cents` equal to that item's snapshot `price_cents`, and HTTP 201

#### Scenario: Return request on a non-delivered order is rejected
- **WHEN** the owning session requests a return on an order whose status is `shipped`
- **THEN** the API returns HTTP 422 with an error indicating only delivered orders are returnable

#### Scenario: Non-owner cannot request a return
- **WHEN** a session that does not own the order (and is not the linked user) requests a return
- **THEN** the API returns HTTP 404

#### Scenario: Requesting more than the remaining returnable quantity is rejected
- **WHEN** a session requests 3 units of an order item that was ordered with quantity 2
- **THEN** the API returns HTTP 422 indicating the requested quantity exceeds what remains returnable

### Requirement: Returns are limited to the return window
A return request SHALL be accepted only when the current time is within
`RETURN_WINDOW_DAYS` (default 14) of the order's delivery timestamp. Requests after the
window SHALL be rejected with HTTP 422.

#### Scenario: Return requested after the window closes
- **WHEN** the owning session requests a return more than `RETURN_WINDOW_DAYS` after the order was delivered
- **THEN** the API returns HTTP 422 indicating the return window has closed

#### Scenario: Return requested on the last day of the window
- **WHEN** the owning session requests a return exactly within `RETURN_WINDOW_DAYS` of delivery
- **THEN** the return is created successfully

### Requirement: Only one open return per order
An order SHALL have at most one open return (status `requested`, `approved`, or
`received`) at a time. A second request while one is open SHALL be rejected with HTTP
409. After a return reaches `rejected` or `cancelled`, a new request is allowed; after
`refunded`, only remaining un-returned quantity is eligible. The invariant SHALL hold
under concurrent requests: the open-return check and the return insert SHALL execute in
a single serialized write transaction, backed by a database constraint that physically
permits at most one open return per order.

#### Scenario: Second return request while one is open
- **WHEN** a session requests a return for an order that already has a `requested` return
- **THEN** the API returns HTTP 409 indicating a return is already open for this order

#### Scenario: Concurrent duplicate requests create at most one open return
- **WHEN** two return requests for the same order arrive concurrently (e.g. a double-click or retry) and no open return yet exists
- **THEN** exactly one return is created and the other request returns HTTP 409, never two open returns

#### Scenario: New request allowed after a prior return was rejected
- **WHEN** a session requests a return for an order whose only prior return is `rejected`
- **THEN** the new return is created successfully

### Requirement: Return state machine enforces valid transitions
The system SHALL enforce return transitions: `requested → approved`,
`requested → rejected`, `requested → cancelled`, `approved → received`,
`approved → rejected`, `received → refunded`. Terminal states (`refunded`, `rejected`,
`cancelled`) SHALL allow no further transitions. Invalid transitions SHALL return HTTP
422.

#### Scenario: Owner approves a requested return
- **WHEN** an admin transitions a `requested` return to `approved` with a note
- **THEN** the return status becomes `approved` and an `approved` event is recorded

#### Scenario: Invalid transition from requested to refunded
- **WHEN** an admin attempts to transition a `requested` return directly to `refunded`
- **THEN** the API returns HTTP 422 indicating an invalid return transition

#### Scenario: No transition from a refunded return
- **WHEN** an admin attempts any transition on a `refunded` return
- **THEN** the API returns HTTP 422 indicating the return is in a terminal state

### Requirement: Customer may cancel only a requested return
The system SHALL expose `POST /v1/orders/{id}/returns/{return_id}/cancel` for the
owning session/user, permitted only while the return is `requested`. Cancelling after
approval SHALL be rejected with HTTP 422.

#### Scenario: Customer cancels a still-requested return
- **WHEN** the owning session cancels a return in status `requested`
- **THEN** the return status becomes `cancelled` and a `cancelled` event is recorded

#### Scenario: Customer cannot cancel an approved return
- **WHEN** the owning session attempts to cancel a return in status `approved`
- **THEN** the API returns HTTP 422

### Requirement: Refund occurs only after goods are received and inspected
A refund SHALL be reachable only from the `received` state. Marking a return `received`
represents the owner physically receiving the returned candle and inspecting it. No
refund SHALL be executed or recorded before `received`. If inspection fails (goods never
arrived or arrived unacceptable), the owner SHALL use `rejected` instead, in which case
no stock is restored and no refund occurs.

#### Scenario: Refund cannot precede receipt
- **WHEN** an admin attempts to refund a return that is still `approved`
- **THEN** the API returns HTTP 422 indicating the return must be received before it can be refunded

#### Scenario: Failed inspection routes to rejection
- **WHEN** an admin rejects an `approved` return because the returned candle arrived damaged beyond the claim
- **THEN** the return becomes `rejected`, no stock is restored, and no refund occurs

### Requirement: Stock is restored when a return is received
When an admin transitions an `approved` return to `received`, the system SHALL restore
product stock by the returned quantity for each return item, within a single
transaction, and stamp `received_at`. Stock SHALL NOT be restored at request time or at
refund time. Because `received` is reachable only once, stock SHALL NOT be
double-restored.

#### Scenario: Receiving a return restores stock
- **WHEN** an admin marks an `approved` return (2 units of product X) as `received`
- **THEN** product X stock increases by 2, `received_at` is set, and a `received` event is recorded

#### Scenario: Receiving tolerates a deleted product
- **WHEN** an admin marks a return `received` for a product that no longer exists
- **THEN** the transition still succeeds, the missing product is logged, and remaining items' stock is restored

### Requirement: Refund amount is computed server-side from order snapshots
The refund amount SHALL equal the sum of each return item's snapshot `price_cents`
multiplied by its returned quantity. Shipping SHALL NOT be included in any refund — the
customer pays shipping to receive the goods and it is not reversed on a return. The
client SHALL NOT supply the amount. The amount SHALL be re-verified against stored
`return_items` immediately before any refund is executed or recorded.

#### Scenario: Refund amount ignores any client-supplied value
- **WHEN** a return request includes an unexpected amount field in its body
- **THEN** the stored `refund_amount_cents` is derived only from item snapshots, ignoring the client value

#### Scenario: Full-order return does not refund shipping
- **WHEN** every item of an order with a non-zero `shipping_cents` is returned and refunded
- **THEN** the refund amount equals the sum of item snapshot prices only and excludes `shipping_cents`

### Requirement: Card returns refund automatically via Stripe
For an order paid by card, transitioning a `received` return to refund SHALL call the
Stripe Refunds API for the order's PaymentIntent with the computed amount, set
`refund_status = pending`, store `stripe_refund_id`, and record a `refund_attempted`
event. The return SHALL become `refunded` only after a verified Stripe refund webhook
(`charge.refunded` / `refund.updated`) confirms success, processed idempotently by
Stripe event id.

#### Scenario: Card refund awaits webhook confirmation
- **WHEN** an admin issues the refund for a received card return
- **THEN** a Stripe refund is created, `refund_status` is `pending`, `stripe_refund_id` is stored, and the return is not yet `refunded`

#### Scenario: Stripe webhook confirms the refund
- **WHEN** a verified `charge.refunded` webhook for the stored refund id is processed
- **THEN** `refund_status` becomes `refunded`, the return status becomes `refunded`, `refunded_at` is set, and the `return_refunded` customer email is queued

#### Scenario: Transient Stripe failure is retryable
- **WHEN** the Stripe Refunds API call fails with a transient error (network, rate limit, 5xx, or any code not on the terminal allowlist)
- **THEN** `refund_status` becomes `failed`, a `refund_failed` event is recorded, the admin is alerted, and the return remains `received` for retry

#### Scenario: Duplicate refund webhook is idempotent
- **WHEN** the same Stripe refund event id is delivered twice
- **THEN** the second delivery makes no further state change

### Requirement: Terminal Stripe refund failures route to manual settlement
When a Stripe refund fails with a **terminal** error — a code on a tight allowlist
(`charge_already_refunded`, `charge_disputed`, charge-not-refundable/expired; verified
against Stripe's API-error and Refund `failure_reason` docs at build) meaning Stripe
structurally cannot refund the charge — the system
SHALL set `refund_status = manual_required`, keep the return in `received`, record the
reason in `return_events`, and NOT move money. Any error code NOT on the allowlist SHALL
be treated as transient (retryable), never as terminal. The owner SHALL then be able to
record a manual refund from `received` for the card order, exactly as for bank/COD,
which moves the return to `refunded`. Classification SHALL apply both to the synchronous
`refund.create` call and to async failures arriving via `refund.updated` webhook,
sharing one allowlist.

#### Scenario: Terminal Stripe error offers manual settlement, does not auto-refund
- **WHEN** a card refund fails with a terminal allowlist code
- **THEN** `refund_status` becomes `manual_required`, the return stays `received`, no money moves, and the reason is recorded

#### Scenario: Owner confirms manual refund for a card order Stripe could not refund
- **WHEN** the owner records a manual refund on a `manual_required` card return
- **THEN** the return becomes `refunded`, `refunded_at` is set, and the `return_refunded` email is queued

#### Scenario: Late Stripe success wins over the manual path
- **WHEN** a `manual_required` return later receives a verified *succeeded* Stripe refund webhook for its stored `stripe_refund_id`
- **THEN** the return becomes `refunded` via Stripe and the manual refund action is blocked (single refund per `stripe_refund_id`)

#### Scenario: Unknown error code is not treated as terminal
- **WHEN** a card refund fails with an error code not on the terminal allowlist
- **THEN** it is treated as transient (`refund_status = failed`, retryable), never `manual_required`


### Requirement: Bank transfer and COD returns are refunded manually
For an order paid by bank transfer or pay-on-delivery, the refund step SHALL NOT call
any payment API. The admin action SHALL record an optional `refund_reference`, set
`refund_status = refunded` and status `refunded` immediately, stamp `refunded_at`,
record a `refund_confirmed` event, and queue the `return_refunded` email. The same
manual settlement action SHALL also be available for card orders whose automated Stripe
refund reached `refund_status = manual_required` (see "Terminal Stripe refund failures
route to manual settlement").

#### Scenario: Manual bank-transfer refund is recorded
- **WHEN** an admin records the refund for a received bank-transfer return with a reference note
- **THEN** the return becomes `refunded`, `refund_reference` is stored, and the customer refund email is queued

### Requirement: Return audit timeline is append-only
Every return transition, admin note, refund attempt, and refund webhook SHALL append a
row to `return_events` with an actor (`customer`, `admin`, or `system`) and timestamp.
Events SHALL never be updated or deleted.

#### Scenario: Full lifecycle produces an ordered event trail
- **WHEN** a return progresses requested → approved → received → refunded
- **THEN** `return_events` contains `requested`, `approved`, `received`, and `refund_confirmed` rows in order, each with an actor

### Requirement: Customer can view their returns
The system SHALL expose `GET /v1/orders/{id}/returns` (and include return summary on
order detail) for the owning session/user, returning the return status, items, refund
status, and refund amount. Non-owners SHALL receive HTTP 404.

#### Scenario: Customer views return status and refund progress
- **WHEN** the owning session fetches returns for their order
- **THEN** the response includes each return's status, returned items, `refund_status`, and `refund_amount_cents`

### Requirement: Customer-facing return status is coarser than the internal state
Customer-facing return status SHALL be presented with a coarser vocabulary than the
internal state machine. The internal `refund_status = pending` (card refund submitted to
Stripe, awaiting webhook) SHALL NOT be shown to the customer as a standalone state; it
SHALL be folded into the `received` presentation. A `refund_status = failed` SHALL NOT be
shown to the customer as a failure. Customer labels: `requested` → "Return requested";
`approved` → "Approved — send it back"; `received` (refund not yet confirmed) → "We've
received your return — refund on the way"; `refunded` → "Refunded"; `rejected` → "Return
declined"; `cancelled` → "Return cancelled".

#### Scenario: Pending Stripe refund is not shown as a scary standalone state
- **WHEN** a customer views a return in `received` with `refund_status = pending`
- **THEN** they see the "refund on the way" presentation, not a bare "pending" state

#### Scenario: Failed Stripe refund is not shown to the customer as failure
- **WHEN** a card refund attempt has `refund_status = failed` and the return is still `received`
- **THEN** the customer still sees "refund on the way" while the owner retries or settles manually

#### Scenario: Admin sees the operational refund sub-state
- **WHEN** an admin views the same `received` return
- **THEN** the admin sees the operational label reflecting `refund_status` (e.g. "Stripe refund pending", "refund failed (retry)", or "awaiting manual refund")

### Requirement: Return requests are rate limited
Return request creation SHALL be limited to a conservative MVP cap per session and per
IP. Exceeding the limit SHALL return HTTP 429.

#### Scenario: Excessive return requests are throttled
- **WHEN** a session exceeds the return-request rate limit within the window
- **THEN** the API returns HTTP 429
