## ADDED Requirements

### Requirement: Periodic batch loading from JSONL to DuckDB
The system SHALL periodically read JSONL buffer files and bulk-insert their contents into the DuckDB events table.

#### Scenario: Normal batch cycle
- **WHEN** the batch interval (default 60 seconds) elapses
- **THEN** the loader reads all `.jsonl` files in the buffer directory, inserts events into DuckDB, and moves processed files to the archive directory

#### Scenario: No files to process
- **WHEN** the batch interval elapses but the buffer directory contains no `.jsonl` files
- **THEN** the loader completes without error and logs nothing

### Requirement: Transaction-per-file atomicity
The system SHALL process each JSONL file in a single DuckDB transaction. A file is either fully loaded or not loaded at all.

#### Scenario: Successful file load
- **WHEN** a buffer file `events_2026-07-04.jsonl` contains 500 valid event lines
- **THEN** all 500 events are inserted in one transaction and the file is moved to `archive/events_2026-07-04.jsonl.done`

#### Scenario: DuckDB error during load
- **WHEN** a transaction fails (e.g., DuckDB internal error)
- **THEN** the transaction is rolled back, the file remains in `buffer/` unchanged, and the error is logged

#### Scenario: File remains after crash
- **WHEN** the process crashes during a batch load
- **THEN** the file stays in `buffer/` (transaction never committed) and is retried on next startup

### Requirement: Event deduplication
The system SHALL deduplicate events using `event_id` as the primary key, ensuring the same event is never stored twice.

#### Scenario: Duplicate event_id from client retry
- **WHEN** a file contains an event with `event_id: "abc"` and DuckDB already has a row with `event_id: "abc"`
- **THEN** the duplicate is silently skipped (INSERT OR IGNORE) and the load continues

#### Scenario: File replayed after partial failure
- **WHEN** a file was partially loaded (some events committed before a crash) and is retried
- **THEN** previously loaded events are skipped via dedup, new events are inserted

### Requirement: Corrupt line handling
The system SHALL skip invalid/corrupt JSON lines in buffer files without failing the entire batch.

#### Scenario: Partial line from crash
- **WHEN** a buffer file has a truncated final line (from a process crash mid-write)
- **THEN** the corrupt line is skipped and all complete lines are loaded successfully

#### Scenario: Malformed JSON line
- **WHEN** a buffer file contains a line that is not valid JSON
- **THEN** that line is skipped (ignore_errors) and remaining lines are processed

### Requirement: File archival after successful load
The system SHALL move successfully loaded files from the buffer directory to the archive directory.

#### Scenario: File archived after commit
- **WHEN** a DuckDB transaction commits successfully for a file
- **THEN** the file is renamed from `buffer/events_YYYY-MM-DD.jsonl` to `archive/events_YYYY-MM-DD.jsonl.done`

#### Scenario: Archive directory auto-created
- **WHEN** the archive directory does not exist
- **THEN** it is created before the first file move

### Requirement: Single-writer enforcement via file lock
The system SHALL use an exclusive file lock (`fcntl.flock`) to ensure only one batch loader instance writes to DuckDB at any given time, across all worker processes.

#### Scenario: First worker acquires lock and runs batch
- **WHEN** a worker's batch loop fires and no other worker holds the lock on `app/data/.batch.lock`
- **THEN** the worker acquires the lock, runs the batch load, and releases the lock after completion

#### Scenario: Second worker skips when lock is held
- **WHEN** a worker's batch loop fires but another worker already holds the lock
- **THEN** the worker skips this batch cycle without error (non-blocking LOCK_NB attempt fails with EWOULDBLOCK)

#### Scenario: Lock auto-released on process death
- **WHEN** the worker holding the lock crashes or is killed
- **THEN** the kernel automatically releases the file lock and another worker can acquire it on the next cycle

### Requirement: Non-blocking batch loading
The system SHALL run DuckDB batch operations without blocking the FastAPI event loop.

#### Scenario: API responds during batch load
- **WHEN** the batch loader is processing files (DuckDB writes in progress)
- **THEN** the event collection API continues to accept and buffer new events with normal latency

### Requirement: DuckDB schema initialization
The system SHALL create the events table and indexes on application startup if they do not exist.

#### Scenario: First startup with empty database
- **WHEN** the application starts and `app/data/duckdb.db` does not exist
- **THEN** the database file is created with the events table (event_id VARCHAR PK, session_id VARCHAR NOT NULL, user_id VARCHAR, event_type VARCHAR NOT NULL, product_id VARCHAR, server_timestamp TIMESTAMPTZ NOT NULL, metadata JSON) and indexes on session_id, server_timestamp, and (event_type, product_id)

#### Scenario: Subsequent startup with existing schema
- **WHEN** the application starts and the events table already exists
- **THEN** startup completes without error (CREATE IF NOT EXISTS)
