## ADDED Requirements

### Requirement: Request correlation ID assigned to every request
The system SHALL generate a UUID4 correlation ID for every incoming HTTP request and make it available throughout the request lifecycle via `contextvars`. If the request includes an `X-Request-ID` header, that value SHALL be used instead of generating a new one (after UUID format validation). The correlation ID SHALL be included in the response as the `X-Request-ID` header.

#### Scenario: Request without X-Request-ID header gets a generated ID
- **WHEN** a request arrives without an `X-Request-ID` header
- **THEN** the system generates a UUID4, stores it in a contextvar, includes it in all log entries for this request, and returns it in the `X-Request-ID` response header

#### Scenario: Request with valid X-Request-ID header uses provided ID
- **WHEN** a request arrives with header `X-Request-ID: 550e8400-e29b-41d4-a716-446655440000`
- **THEN** the system uses that ID as the correlation ID for this request and returns it in the response header

#### Scenario: Request with invalid X-Request-ID header gets a generated ID
- **WHEN** a request arrives with header `X-Request-ID: not-a-uuid`
- **THEN** the system ignores the invalid value, generates a new UUID4, and uses that as the correlation ID

### Requirement: Structured JSON logging in production
The system SHALL use `structlog` configured with JSON output in production mode and colored console output in development mode. Every log entry SHALL automatically include: `timestamp` (ISO 8601), `level`, `request_id` (from correlation ID contextvar), `event` (the log message), and `logger` (the module name).

#### Scenario: Production log entry format
- **WHEN** a service logs `logger.info("Order created", order_id="abc-123")` in production mode
- **THEN** the output is a single JSON line containing `{"timestamp": "...", "level": "info", "request_id": "...", "event": "Order created", "order_id": "abc-123", "logger": "app.services.order_service"}`

#### Scenario: Development log entry format
- **WHEN** a service logs `logger.info("Order created", order_id="abc-123")` in development mode
- **THEN** the output is human-readable colored text with timestamp, level, request_id, event, and extra fields

### Requirement: Service-layer operations emit structured logs
The system SHALL log at entry and exit of critical service operations: checkout, stock changes, authentication, session rotation, and admin mutations. Logs SHALL include operation-specific context (e.g., `order_id`, `product_id`, `session_id`, `user_id`) as structured fields. Error paths SHALL log at ERROR level with the exception type and message.

#### Scenario: Checkout logs operation lifecycle
- **WHEN** a checkout operation succeeds
- **THEN** the system emits at minimum: an INFO log at operation start (with session_id, item_count), and an INFO log at operation end (with order_id, total_cents, duration_ms)

#### Scenario: Failed operation logs error with context
- **WHEN** a checkout fails due to insufficient stock
- **THEN** the system emits an ERROR log with the exception type, product_id, requested quantity, available quantity, and session_id — all as structured fields (not concatenated into the message string)

### Requirement: Log output destination is stdout
The system SHALL write all log output to stdout. The system SHALL NOT manage log files or rotation directly — that responsibility belongs to the process supervisor (systemd/journald).

#### Scenario: Application logs appear on stdout
- **WHEN** the application is running and any log event occurs
- **THEN** the log output appears on stdout (file descriptor 1), not stderr or a file
