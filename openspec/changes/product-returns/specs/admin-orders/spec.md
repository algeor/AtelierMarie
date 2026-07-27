## ADDED Requirements

### Requirement: Admin returns queue
The system SHALL expose `GET /v1/admin/returns` returning a paginated list of returns
with optional `status` filter, sorted by `created_at` descending. Each entry SHALL
include the linked order number, return status, refund status, refund amount, and item
count. Access SHALL require admin authorization.

#### Scenario: Admin lists pending returns
- **WHEN** an admin sends `GET /v1/admin/returns?status=requested`
- **THEN** the API returns all returns in status `requested`, newest first, with total/page/limit

#### Scenario: Non-admin denied
- **WHEN** a non-admin session sends `GET /v1/admin/returns`
- **THEN** the API returns HTTP 401/403 per the admin auth convention

### Requirement: Admin return detail and actions
The system SHALL expose `GET /v1/admin/returns/{return_id}` (full detail incl. item
breakdown, refund state, and the `return_events` timeline) and action endpoints to
`approve`, `reject`, `receive`, and `refund` a return. The `approve`, `reject`,
`receive`, and manual `refund` actions SHALL each require a non-empty admin note
persisted to `return_events`.

#### Scenario: Admin approves a return with a note
- **WHEN** an admin approves a `requested` return with a note
- **THEN** the return becomes `approved`, the note is stored on the `approved` event, and the `return_approved` email is queued

#### Scenario: Approve without a note is rejected
- **WHEN** an admin approves a return with an empty note
- **THEN** the API returns HTTP 422 requiring an admin note

#### Scenario: Admin rejects a return
- **WHEN** an admin rejects a `requested` or `approved` return with a note
- **THEN** the return becomes `rejected`, no stock is restored, no refund occurs, and the `return_rejected` email is queued

#### Scenario: Return detail includes the audit timeline
- **WHEN** an admin fetches a return's detail
- **THEN** the response includes the ordered `return_events` timeline with actors and notes

### Requirement: Admin order detail surfaces linked returns
Admin order detail SHALL show any returns linked to the order, including per-item
returned quantities and each return's refund state, and SHALL expose a "start return on
behalf of customer" affordance for delivered orders.

#### Scenario: Order detail shows a linked return
- **WHEN** an admin views a delivered order that has a return
- **THEN** the order detail lists the return with its status, returned items, and refund status

### Requirement: Dashboard revenue is net of confirmed refunds
Dashboard revenue SHALL subtract `refund_amount_cents` for every return whose
`refund_status` is `refunded`. Pending or failed refunds SHALL NOT reduce revenue.

#### Scenario: Confirmed refund reduces revenue
- **WHEN** a card return reaches `refunded` for EUR 20 on a EUR 50 order
- **THEN** dashboard revenue for that order contributes EUR 30

#### Scenario: Pending refund does not reduce revenue
- **WHEN** a return's refund is still `pending`
- **THEN** dashboard revenue is not yet reduced by that return
