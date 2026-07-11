## ADDED Requirements

### Requirement: Exception catches are specific to expected failure modes
The system SHALL catch only the specific exception types that each operation can legitimately raise. Bare `except Exception:` blocks SHALL NOT exist in production code paths. Each catch block SHALL handle a known failure mode with an appropriate recovery or escalation strategy.

#### Scenario: Database operation catches specific SQLite errors
- **WHEN** a database write operation fails
- **THEN** the catch block handles `sqlite3.IntegrityError` (constraint violation) and `sqlite3.OperationalError` (lock timeout, disk full) separately, with different recovery logic for each

#### Scenario: No bare except in service layer
- **WHEN** any service function encounters an exception
- **THEN** the exception is either a specific caught type with appropriate handling, or propagates uncaught to the route layer (where it becomes a 500 with logging)

### Requirement: Exception chaining preserves root cause
The system SHALL chain all re-raised exceptions using `raise NewError(...) from original_error`. The original exception SHALL be preserved in the `__cause__` attribute for debugging. Direct `raise` without context enrichment is acceptable only when the exception already contains sufficient context.

#### Scenario: Service exception chains from database error
- **WHEN** an `sqlite3.IntegrityError` occurs during stock decrement
- **THEN** the service raises `InsufficientStockError(product_id, requested, available) from e` where `e` is the original IntegrityError

#### Scenario: Exception chain visible in traceback
- **WHEN** an unhandled exception reaches the top-level error handler
- **THEN** the full chain is visible: the application exception AND its `__cause__` (the original error)

### Requirement: Every caught exception is logged with context
The system SHALL log every caught exception at the appropriate level (ERROR for unexpected failures, WARNING for expected-but-notable conditions like stock exhaustion). Log entries SHALL include: the operation being performed, the exception type and message, and relevant entity IDs (order_id, product_id, session_id).

#### Scenario: Caught IntegrityError during checkout is logged
- **WHEN** a stock CHECK constraint is violated during checkout
- **THEN** the system logs at WARNING level with fields: `event="Stock constraint violated"`, `product_id=...`, `session_id=...`, `exc_type="IntegrityError"`

#### Scenario: Unexpected error in CSV import row is logged
- **WHEN** an unexpected exception occurs processing CSV row 42
- **THEN** the system logs at ERROR level with `exc_info=True` (full traceback), `row_number=42`, and the exception message — before adding a user-friendly error to the row-level errors list

### Requirement: Route layer translates service exceptions to HTTP responses
The system SHALL map service-layer custom exceptions to HTTP status codes in the route layer. The mapping SHALL be: `NotFoundError` → 404, `InsufficientStockError` → 409, `DuplicateError` → 409, `InvalidStateTransitionError` → 422, `AuthenticationError` → 401, `AuthorizationError` → 403. Unmapped exceptions SHALL result in 500 with a generic message (never leaking internal details).

#### Scenario: Unknown exception returns safe 500
- **WHEN** a service raises an exception type not in the mapping (e.g., `RuntimeError`)
- **THEN** the route returns HTTP 500 with body `{"error": {"code": "INTERNAL_ERROR", "message": "An internal error occurred"}}` and logs the full exception with traceback

#### Scenario: Mapped exception returns correct status code
- **WHEN** a service raises `InsufficientStockError`
- **THEN** the route returns HTTP 409 with structured error details (product_id, requested, available)
