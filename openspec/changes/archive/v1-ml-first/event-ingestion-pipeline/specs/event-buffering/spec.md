## ADDED Requirements

### Requirement: Append events to date-partitioned JSONL files
The system SHALL write each event as a single JSON line to a file named `events_YYYY-MM-DD.jsonl` in the buffer directory.

#### Scenario: Event written to today's partition
- **WHEN** an event is accepted on 2026-07-05
- **THEN** it is appended as a JSON line to `app/data/events/buffer/events_2026-07-05.jsonl`

#### Scenario: Date rollover creates new file
- **WHEN** the first event arrives on a new calendar day (2026-07-06)
- **THEN** a new file `events_2026-07-06.jsonl` is created in the buffer directory

### Requirement: Thread-safe concurrent writes
The system SHALL safely handle concurrent event writes from multiple threads without data corruption or interleaving.

#### Scenario: Concurrent writes from multiple request handlers
- **WHEN** 10 concurrent requests each write an event simultaneously
- **THEN** all 10 events appear as complete, valid JSON lines in the buffer file (no partial lines, no interleaving)

#### Scenario: Multi-worker process writes
- **WHEN** multiple uvicorn worker processes append to the same JSONL file
- **THEN** each line is atomically written (O_APPEND guarantees on POSIX)

### Requirement: Crash safety for buffered events
The system SHALL ensure that events acknowledged to the client (202 response) are durable on disk.

#### Scenario: Process crash after response
- **WHEN** the server process crashes after returning 202 to the client
- **THEN** the event is present in the JSONL buffer file (line-buffered flush guarantees data on disk before response)

#### Scenario: Process crash mid-write
- **WHEN** the server process is killed during a write syscall
- **THEN** at most one event (the in-progress write) may be corrupted as an incomplete line
- **AND** all previously written events remain intact

### Requirement: Event size safety limit
The system SHALL reject events that exceed a configurable maximum size.

#### Scenario: Oversized event rejected
- **WHEN** an event serializes to JSON larger than 8192 bytes
- **THEN** the writer raises an error and the API returns HTTP 413

### Requirement: Buffer directory auto-creation
The system SHALL create the buffer and archive directories if they do not exist.

#### Scenario: First startup with no data directory
- **WHEN** the application starts and `app/data/events/buffer/` does not exist
- **THEN** the directory is created automatically before any writes occur

### Requirement: Graceful shutdown flushes buffers
The system SHALL flush all in-memory buffers and close file handles on shutdown.

#### Scenario: Application shutdown
- **WHEN** the application receives a shutdown signal (SIGTERM)
- **THEN** all buffered data is flushed to disk and file handles are closed before process exit
