## ADDED Requirements

### Requirement: JWKS cache is thread-safe
The system SHALL protect the module-level `_JwksCache` instance with a `threading.Lock`. Read access to cached keys SHALL be lock-free when the cache is fresh (double-checked locking pattern). Write access (cache refresh) SHALL hold the lock for the duration of the update. Only one thread SHALL fetch from Google's JWKS endpoint at a time; concurrent requests SHALL wait for the in-progress fetch rather than initiating duplicate requests.

#### Scenario: Concurrent JWT validations do not corrupt cache
- **WHEN** 10 concurrent requests all trigger JWT validation while the JWKS cache is stale
- **THEN** exactly one HTTP request is made to Google's JWKS endpoint, all 10 requests receive valid key data, and no `KeyError` or partial-read occurs

#### Scenario: Cache read is lock-free when fresh
- **WHEN** the JWKS cache was refreshed less than 1 hour ago and a JWT validation occurs
- **THEN** the key lookup does NOT acquire the lock (no contention with concurrent refreshes)

### Requirement: Checkout transaction uses BEGIN IMMEDIATE
The checkout service SHALL start its transaction with `BEGIN IMMEDIATE` to acquire a reserved (write) lock at transaction start. This prevents the TOCTOU race condition where stock is validated in one statement and decremented in a later statement, with another transaction modifying stock in between.

#### Scenario: Concurrent checkouts for last item are serialized
- **WHEN** two concurrent requests attempt to check out the last unit of product X
- **THEN** the second transaction receives `SQLITE_BUSY` immediately (not after executing statements), retries or fails with 409, and stock never goes negative

#### Scenario: Read-only operations are not blocked by checkout
- **WHEN** a checkout transaction holds the write lock
- **THEN** `GET /v1/products` and `GET /v1/cart` requests complete normally (SQLite WAL allows concurrent reads)

### Requirement: Background cleanup task lifecycle is managed
The system SHALL properly manage the session cleanup background task: (1) on startup, the task is created and stored, (2) on shutdown, the task is cancelled AND awaited with a timeout, (3) `CancelledError` is caught and logged at INFO level, (4) if the task does not terminate within 5 seconds, it is logged at WARNING and abandoned.

#### Scenario: Graceful shutdown awaits cleanup task
- **WHEN** the application receives a shutdown signal while the cleanup task is running
- **THEN** the task is cancelled, awaited (with 5s timeout), and the shutdown proceeds cleanly without `asyncio` warnings about pending tasks

#### Scenario: Cleanup task mid-operation is not corrupted
- **WHEN** the cleanup task is in the middle of deleting expired sessions and shutdown occurs
- **THEN** the current DELETE operation completes (or rolls back) before the task exits — no half-deleted state
