## ADDED Requirements

### Requirement: Health check endpoint
The system SHALL expose a `GET /health` endpoint that reports pipeline status without authentication.

#### Scenario: Healthy system
- **WHEN** client sends GET /health and the system is operating normally
- **THEN** system returns HTTP 200 with JSON containing: `status: "healthy"`, `buffer_files` (count), `last_batch_at` (timestamp or null), `duckdb_total_events` (integer)

#### Scenario: DuckDB unreachable
- **WHEN** client sends GET /health but DuckDB connection fails
- **THEN** system returns HTTP 200 with `status: "degraded"` and `duckdb_error` field describing the issue

#### Scenario: Buffer directory unwritable
- **WHEN** client sends GET /health but the buffer directory is not writable
- **THEN** system returns HTTP 200 with `status: "degraded"` and `buffer_error` field

### Requirement: Buffer size visibility
The system SHALL report the approximate number of unbatched events in the health response.

#### Scenario: Events pending in buffer
- **WHEN** there are 3 JSONL files in the buffer directory totaling approximately 1500 lines
- **THEN** health endpoint reports `buffer_files: 3` and `buffer_events_approx` with an estimated count

### Requirement: Last batch timestamp tracking
The system SHALL track and expose when the last successful batch load completed.

#### Scenario: After first batch completes
- **WHEN** the batch loader successfully loads files at 14:30:00 UTC
- **THEN** health endpoint reports `last_batch_at: "2026-07-05T14:30:00Z"`

#### Scenario: No batch has run yet
- **WHEN** the application just started and no batch has completed
- **THEN** health endpoint reports `last_batch_at: null`
