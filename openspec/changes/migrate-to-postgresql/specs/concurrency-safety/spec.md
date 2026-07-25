## MODIFIED Requirements

### Requirement: Checkout transaction uses row-level locking
The checkout service SHALL start a Postgres transaction and acquire row-level locks on every product involved in the cart via `SELECT ... FOR UPDATE ORDER BY id ASC` before validating or updating stock. This prevents the TOCTOU race condition where stock is validated in one statement and decremented in a later statement, with another transaction modifying stock in between. Locks SHALL be acquired in ascending `id` order so that concurrent multi-product checkouts cannot deadlock.

#### Scenario: Concurrent checkouts for last item are serialized
- **WHEN** two concurrent requests attempt to check out the last unit of product X
- **THEN** the first transaction's `SELECT ... FOR UPDATE` acquires the row lock, validates stock=1, decrements to 0, and commits
- **AND** the second transaction blocks on the lock, then upon acquisition sees stock=0, rolls back, and returns HTTP 409
- **AND** stock never goes negative

#### Scenario: Read-only operations are not blocked by checkout
- **WHEN** a checkout transaction holds `FOR UPDATE` locks on some product rows
- **THEN** `GET /v1/products` and `GET /v1/cart` requests complete normally (Postgres readers do not block on writer row locks unless they take `FOR UPDATE` themselves)

#### Scenario: Multi-product checkout uses deterministic lock order
- **WHEN** two concurrent checkouts each contain products X and Y in different input orders
- **THEN** both lock the rows in the same ascending `id` order and no deadlock occurs

## ADDED Requirements

### Requirement: Deadlocks retried once at service layer
When a Postgres transaction fails with SQLSTATE `40P01` (deadlock detected), the service SHALL retry the entire transaction one time. If the retry also raises `40P01`, the service SHALL raise a `RetryableError` which the route layer maps to HTTP 409 with a message indicating transient contention.

#### Scenario: Single deadlock is recovered
- **WHEN** a checkout transaction receives `40P01` on its first attempt but the retry succeeds
- **THEN** the client receives HTTP 201 with the created order and a single INFO log records the retry

#### Scenario: Repeated deadlock surfaces to client
- **WHEN** both the first attempt and the retry raise `40P01`
- **THEN** the client receives HTTP 409, a WARNING log records both failures with the retry marker, and no order is created
