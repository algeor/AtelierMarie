## ADDED Requirements

### Requirement: Database query duration recorded on service operations
The system SHALL record and log the duration of database operations that span more than a single simple query — specifically checkout, admin CSV import, product search, and admin listing endpoints. Duration SHALL be reported as a structured `db_duration_ms` field on the operation's completion log entry.

#### Scenario: Checkout logs db duration
- **WHEN** a checkout operation completes
- **THEN** its completion log entry includes `db_duration_ms=<int>` alongside `order_id`, `total_cents`, and `session_id`

#### Scenario: Product search logs db duration
- **WHEN** a search query is executed
- **THEN** the service emits a DEBUG-level log entry with `event="products.search"`, `q_length=<int>`, `locale=<str>`, `result_count=<int>`, `db_duration_ms=<int>` — never the raw query text (to avoid leaking user input into logs at higher volumes)

### Requirement: Pool saturation warnings emitted
The system SHALL emit a structured WARNING log entry when the asyncpg pool reports zero free connections at acquire time. The entry SHALL include `event="db pool saturated"`, `pool_size=<int>`, and `wait_start_ms=<int>`.

#### Scenario: Pool saturation logged once per event
- **WHEN** a request arrives and all pool connections are in use, causing the acquire to wait
- **THEN** exactly one WARNING log entry is emitted for that acquire event (not one per millisecond of waiting)

#### Scenario: No saturation warning when free connections exist
- **WHEN** a request acquires a pool connection with free capacity available
- **THEN** no saturation log entry is emitted (only the DEBUG-level acquire trace if enabled)

### Requirement: Postgres SQLSTATE included in error logs
Log entries for caught `asyncpg.PostgresError` subclasses SHALL include a `sqlstate` structured field containing the five-character SQLSTATE code from the original exception. This aids incident diagnosis by making the exact Postgres error class searchable in log aggregation.

#### Scenario: Check violation log includes sqlstate
- **WHEN** an `asyncpg.exceptions.CheckViolationError` is caught
- **THEN** the resulting log entry contains `sqlstate="23514"`

#### Scenario: Deadlock log includes sqlstate
- **WHEN** an `asyncpg.exceptions.DeadlockDetectedError` triggers the retry path
- **THEN** the retry log entry contains `sqlstate="40P01"`
