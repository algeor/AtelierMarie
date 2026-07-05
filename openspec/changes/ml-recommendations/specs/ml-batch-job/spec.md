## ADDED Requirements

### Requirement: Batch job precomputes recommendations
The batch job SHALL precompute top-N recommendations by reading from the shared analytics layer's `analytics_*` tables and caching the results in memory.

#### Scenario: Active sessions precomputed
- **WHEN** the batch job runs
- **THEN** recommendations are precomputed for all sessions with activity in the last 30 minutes

#### Scenario: Trending products precomputed
- **WHEN** the batch job runs
- **THEN** the global trending product list is computed and stored in the cache

#### Scenario: Analytics tables read as input
- **WHEN** the batch job precomputes recommendations
- **THEN** it reads from `analytics_popularity`, `analytics_cooccurrence`, `analytics_ctr`, and `analytics_session_sequences`

### Requirement: Batch job requires no write lock
The batch job SHALL NOT acquire any file lock. It only reads from DuckDB (`analytics_*` tables) and writes to the in-memory recommendation cache. Since it performs no DuckDB writes, there is no contention with the event batch loader or the analytics layer's compute job.

#### Scenario: No lock acquired
- **WHEN** the batch job executes
- **THEN** it does not attempt to acquire `.ml-compute.lock` or any other file lock

#### Scenario: Concurrent execution with analytics layer
- **WHEN** the analytics layer is rebuilding feature tables while the ML batch job reads them
- **THEN** the ML batch job either reads the previous complete snapshot (DuckDB MVCC) or retries on the next scheduled run — no corruption occurs

### Requirement: Batch job logs computation statistics
The batch job SHALL log computation statistics after each run, including: total duration, number of sessions precomputed, number of trending products computed, and any errors encountered.

#### Scenario: Successful run logging
- **WHEN** the batch job completes successfully
- **THEN** a log entry is emitted with duration_seconds, sessions_precomputed count, trending_products count, and status="success"

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

#### Scenario: Recommendation precomputation completes within time budget
- **WHEN** the system has fewer than 10,000 active sessions
- **THEN** the batch job completes recommendation precomputation in under 10 seconds
