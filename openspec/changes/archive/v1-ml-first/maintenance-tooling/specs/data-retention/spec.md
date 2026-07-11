## ADDED Requirements

### Requirement: Archive file retention enforcement
The system SHALL delete JSONL archive files (`.done` files) from `app/data/events/archive/` that are older than 30 days when the cleanup command is executed.

#### Scenario: Archive files older than 30 days are deleted
- **WHEN** the cleanup command is executed AND archive files with modification timestamps older than 30 days exist
- **THEN** those files SHALL be deleted and the count and total bytes freed SHALL be logged

#### Scenario: Archive files younger than 30 days are preserved
- **WHEN** the cleanup command is executed AND archive files have modification timestamps within the last 30 days
- **THEN** those files SHALL NOT be deleted

### Requirement: DuckDB events retention enforcement
The system SHALL delete rows from the DuckDB events table where `server_timestamp` is older than 90 days when the cleanup command is executed.

#### Scenario: Old events are deleted
- **WHEN** the cleanup command is executed AND events with `server_timestamp` older than 90 days exist
- **THEN** those rows SHALL be deleted and the count SHALL be logged

#### Scenario: Recent events are preserved
- **WHEN** the cleanup command is executed AND events have `server_timestamp` within the last 90 days
- **THEN** those rows SHALL NOT be deleted

### Requirement: DuckDB expired session retention enforcement
The system SHALL delete rows from the DuckDB session_identity table where `last_seen` is older than 90 days AND `is_expired = TRUE` when the cleanup command is executed.

#### Scenario: Old expired sessions are deleted
- **WHEN** the cleanup command is executed AND session_identity rows have `last_seen` older than 90 days AND `is_expired = TRUE`
- **THEN** those rows SHALL be deleted and the count SHALL be logged

#### Scenario: Active sessions are preserved regardless of age
- **WHEN** the cleanup command is executed AND session_identity rows have `is_expired = FALSE`
- **THEN** those rows SHALL NOT be deleted regardless of their `last_seen` timestamp

#### Scenario: Recently expired sessions are preserved
- **WHEN** the cleanup command is executed AND session_identity rows have `is_expired = TRUE` AND `last_seen` within the last 90 days
- **THEN** those rows SHALL NOT be deleted

### Requirement: Mutual exclusion during cleanup
The system SHALL acquire an exclusive file lock at `app/data/.maintenance.lock` before performing any cleanup operations. If the lock cannot be acquired, the command SHALL exit with an error message indicating another process holds the lock.

#### Scenario: Lock acquired successfully
- **WHEN** the cleanup command is executed AND no other process holds the maintenance lock
- **THEN** the lock SHALL be acquired and cleanup SHALL proceed

#### Scenario: Lock held by another process
- **WHEN** the cleanup command is executed AND another process holds the maintenance lock
- **THEN** the command SHALL exit with a non-zero status and print an error message indicating the lock is held

### Requirement: Dry-run mode for cleanup
The system SHALL support a `--dry-run` flag that reports what would be deleted without performing any actual deletions.

#### Scenario: Dry-run shows pending deletions
- **WHEN** the cleanup command is executed with `--dry-run`
- **THEN** the system SHALL report file counts, row counts, and estimated space that would be freed WITHOUT actually deleting anything

### Requirement: Cleanup logging
The system SHALL log all cleanup actions with timestamps, item counts, and bytes freed to stdout in a structured format.

#### Scenario: Successful cleanup produces summary log
- **WHEN** the cleanup command completes successfully
- **THEN** a summary SHALL be printed showing: archive files deleted (count + bytes), DuckDB events deleted (count), DuckDB sessions deleted (count), and total estimated space freed
