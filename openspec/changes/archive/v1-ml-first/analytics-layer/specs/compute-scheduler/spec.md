## ADDED Requirements

### Requirement: Analytics job runs on 5-minute schedule
The analytics compute job SHALL execute on a 5-minute recurring schedule as a background task within the FastAPI application lifespan.

#### Scenario: Regular execution
- **WHEN** 5 minutes have elapsed since the last analytics run
- **THEN** the analytics job triggers automatically

#### Scenario: Tier 2 conditional execution
- **WHEN** the analytics job runs
- **AND** fewer than 30 minutes have elapsed since the last Tier 2 rebuild
- **THEN** only Tier 1 tables are rebuilt

#### Scenario: Tier 2 triggered after 30 minutes
- **WHEN** the analytics job runs
- **AND** 30 or more minutes have elapsed since the last Tier 2 rebuild
- **THEN** both Tier 1 and Tier 2 tables are rebuilt

### Requirement: Lock acquisition with timeout
The analytics job SHALL acquire `.batch.lock` with a blocking wait of up to 60 seconds before proceeding.

#### Scenario: Lock acquired immediately
- **WHEN** no other process holds `.batch.lock`
- **THEN** the analytics job acquires it and proceeds

#### Scenario: Lock held briefly by event loader
- **WHEN** the event batch loader holds `.batch.lock` for ~100ms
- **THEN** the analytics job waits and acquires the lock once released

#### Scenario: Lock timeout exceeded
- **WHEN** `.batch.lock` is held for more than 60 seconds
- **THEN** the analytics job logs a warning and skips this cycle

#### Scenario: Lock released on failure
- **WHEN** the analytics job encounters an error during computation
- **THEN** `.batch.lock` is released (via context manager)

### Requirement: On-demand CLI trigger
The analytics compute job SHALL be triggerable via CLI command `python -m app.analytics` for development and debugging.

#### Scenario: CLI forces full rebuild
- **WHEN** a developer runs `python -m app.analytics --full`
- **THEN** both Tier 1 and Tier 2 tables are rebuilt regardless of time gate

#### Scenario: CLI respects lock
- **WHEN** CLI trigger runs while `.batch.lock` is held
- **THEN** it waits (up to 60s) like the scheduled job

### Requirement: Compute statistics logging
The analytics job SHALL log statistics after each run: total duration, rows per table, whether tier2 ran, and any errors.

#### Scenario: Successful run
- **WHEN** the analytics job completes successfully
- **THEN** a log entry contains: duration_ms, tables_rebuilt (list), rows_per_table (dict), tier2_ran (bool)

#### Scenario: Partial failure
- **WHEN** one table rebuild fails but others succeed
- **THEN** the log entry includes the error, and successfully rebuilt tables are preserved

### Requirement: Health endpoint exposes analytics status
The health endpoint SHALL include analytics freshness information: `analytics_last_run` (ISO timestamp), `analytics_tier2_last_run` (ISO timestamp), and `analytics_duration_ms` (last run duration).

#### Scenario: Health shows freshness
- **WHEN** a client requests the health endpoint
- **THEN** response includes analytics timing metadata
