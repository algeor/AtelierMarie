## ADDED Requirements

### Requirement: Batch job rebuilds all feature tables
The system SHALL provide a batch computation job that rebuilds all feature tables (features_item_popularity, features_cooccurrence, features_session_sequences, features_ctr) by executing DROP + CREATE AS SELECT for each table.

#### Scenario: Full rebuild on execution
- **WHEN** the batch job executes
- **THEN** all four feature tables are dropped and recreated from the current events data

#### Scenario: Rebuild order
- **WHEN** the batch job runs
- **THEN** feature tables are rebuilt in dependency order (item_popularity and CTR first, then co-occurrence and session sequences)

### Requirement: Batch job precomputes recommendations
After rebuilding feature tables, the batch job SHALL precompute top-N recommendations for recently active sessions and cache the results.

#### Scenario: Active sessions precomputed
- **WHEN** the batch job completes feature table rebuild
- **THEN** recommendations are precomputed for all sessions with activity in the last 30 minutes

#### Scenario: Trending products precomputed
- **WHEN** the batch job runs
- **THEN** the global trending product list is computed and stored in the cache

### Requirement: Batch job acquires file lock
The batch job SHALL acquire an exclusive file lock at `app/data/.ml-compute.lock` before performing any DuckDB writes. The lock MUST be released after completion (success or failure).

#### Scenario: Lock acquired successfully
- **WHEN** no other process holds the ML compute lock
- **THEN** the batch job acquires the lock and proceeds with computation

#### Scenario: Lock already held
- **WHEN** another process holds the ML compute lock
- **THEN** the batch job waits (with configurable timeout) or exits gracefully with a logged warning

#### Scenario: Lock released on failure
- **WHEN** the batch job encounters an error during computation
- **THEN** the file lock is released (via context manager / finally block)

### Requirement: Batch job logs computation statistics
The batch job SHALL log computation statistics after each run, including: total duration, rows processed per feature table, number of sessions precomputed, and any errors encountered.

#### Scenario: Successful run logging
- **WHEN** the batch job completes successfully
- **THEN** a log entry is emitted with duration_seconds, rows per table (dict), sessions_precomputed count, and status="success"

#### Scenario: Failed run logging
- **WHEN** the batch job fails mid-execution
- **THEN** a log entry is emitted with the error message, partial stats, and status="failed"

### Requirement: Batch job runs on schedule and on-demand
The system SHALL support triggering the batch job both on a recurring schedule (default: every 30 minutes) and on-demand via CLI command.

#### Scenario: Scheduled execution
- **WHEN** 30 minutes have elapsed since the last batch run
- **THEN** the batch job is triggered automatically

#### Scenario: CLI trigger
- **WHEN** a developer runs the batch job via CLI (e.g., `python -m app.jobs.ml_compute`)
- **THEN** the job executes immediately regardless of schedule

#### Scenario: Computation completes within time budget
- **WHEN** the system has fewer than 1,000,000 events
- **THEN** the batch job completes in under 60 seconds