## MODIFIED Requirements

### Requirement: Exception catches are specific to expected failure modes
The system SHALL catch only the specific exception types that each operation can legitimately raise. Bare `except Exception:` blocks SHALL NOT exist in production code paths. Each catch block SHALL handle a known failure mode with an appropriate recovery or escalation strategy.

#### Scenario: Database operation catches specific asyncpg errors
- **WHEN** a database write operation fails
- **THEN** the catch block handles `asyncpg.exceptions.UniqueViolationError` (SQLSTATE `23505`), `asyncpg.exceptions.CheckViolationError` (`23514`), `asyncpg.exceptions.ForeignKeyViolationError` (`23503`), `asyncpg.exceptions.DeadlockDetectedError` (`40P01`), and `asyncpg.exceptions.PostgresConnectionError` separately, with different recovery logic for each

#### Scenario: No bare except in service layer
- **WHEN** any service function encounters an exception
- **THEN** the exception is either a specific caught type with appropriate handling, or propagates uncaught to the route layer (where it becomes a 500 with logging)

### Requirement: Exception chaining preserves root cause
The system SHALL chain all re-raised exceptions using `raise NewError(...) from original_error`. The original exception SHALL be preserved in the `__cause__` attribute for debugging. Direct `raise` without context enrichment is acceptable only when the exception already contains sufficient context.

#### Scenario: Service exception chains from database error
- **WHEN** an `asyncpg.exceptions.CheckViolationError` fires on a `stock >= 0` constraint violation during stock decrement
- **THEN** the service raises `InsufficientStockError(product_id, requested, available) from e` where `e` is the original CheckViolationError

#### Scenario: Duplicate key chains to DuplicateError
- **WHEN** an admin CSV import row triggers `asyncpg.exceptions.UniqueViolationError` on the products primary key
- **THEN** the service raises `DuplicateError(entity="product", id=...) from e`

#### Scenario: Exception chain visible in traceback
- **WHEN** an unhandled exception reaches the top-level error handler
- **THEN** the full chain is visible: the application exception AND its `__cause__` (the original error)

### Requirement: Every caught exception is logged with context
The system SHALL log every caught exception at the appropriate level (ERROR for unexpected failures, WARNING for expected-but-notable conditions like stock exhaustion). Log entries SHALL include: the operation being performed, the exception type and message, and relevant entity IDs (order_id, product_id, session_id). For Postgres exceptions, the SQLSTATE code SHALL be included as a structured field.

#### Scenario: Caught CheckViolationError during checkout is logged
- **WHEN** the stock CHECK constraint is violated during checkout (defense-in-depth backup to the row lock)
- **THEN** the system logs at WARNING level with fields: `event="Stock constraint violated"`, `product_id=...`, `session_id=...`, `exc_type="CheckViolationError"`, `sqlstate="23514"`

#### Scenario: Deadlock detected is logged with retry marker
- **WHEN** a checkout transaction receives `DeadlockDetectedError` and enters the single-retry path
- **THEN** the system logs at INFO level: `event="Transaction deadlock, retrying"`, `sqlstate="40P01"`, `session_id=...`, `attempt=1`

#### Scenario: Unexpected error in CSV import row is logged
- **WHEN** an unexpected exception occurs processing CSV row 42
- **THEN** the system logs at ERROR level with `exc_info=True` (full traceback), `row_number=42`, and the exception message — before adding a user-friendly error to the row-level errors list

## ADDED Requirements

### Requirement: Connection pool exhaustion logged and surfaced
When an operation waits more than 5 seconds to acquire a connection from the asyncpg pool, the system SHALL log at WARNING level with `event="db pool acquire slow"`, `wait_ms=...`, `pool_size=...`, `pool_free=...`. If acquisition times out entirely (default 60s), the operation SHALL raise `DatabaseUnavailableError` which the route layer maps to HTTP 503.

#### Scenario: Slow pool acquire is logged
- **WHEN** an operation takes 5.2 seconds to acquire a pool connection
- **THEN** a WARNING log entry is emitted with the wait duration and current pool utilization

#### Scenario: Pool timeout returns 503
- **WHEN** the pool cannot supply a connection within the configured timeout
- **THEN** the service raises `DatabaseUnavailableError` and the route returns HTTP 503 with body `{"error": {"code": "DATABASE_UNAVAILABLE", "message": "Service temporarily unavailable"}}`
