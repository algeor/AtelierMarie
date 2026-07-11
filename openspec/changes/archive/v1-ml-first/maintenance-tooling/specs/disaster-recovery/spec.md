## ADDED Requirements

### Requirement: DuckDB rebuild from archive files
The system SHALL create a new DuckDB database from archived JSONL files when the rebuild-duckdb command is executed with `--archive-dir <path>` and `--output <path>`.

#### Scenario: Fresh database created from archive
- **WHEN** the rebuild-duckdb command is executed with a valid archive directory and output path
- **THEN** a new DuckDB database SHALL be created at the output path with the events table schema and all indexes, populated from the archive files

#### Scenario: Archive files processed in chronological order
- **WHEN** the rebuild processes archive files
- **THEN** files SHALL be sorted by filename/date and processed sequentially to maintain temporal ordering

#### Scenario: Deduplication via INSERT OR IGNORE
- **WHEN** the rebuild encounters duplicate event_ids across multiple archive files
- **THEN** duplicates SHALL be skipped via INSERT OR IGNORE and the duplicate count SHALL be reported

#### Scenario: Corrupt JSONL lines skipped
- **WHEN** the rebuild encounters unparseable lines in archive files
- **THEN** those lines SHALL be skipped with a warning, and the total corrupt line count SHALL be reported at completion

### Requirement: Rebuild never overwrites existing database
The system SHALL write only to the specified output path and SHALL refuse to proceed if the output file already exists.

#### Scenario: Output path already exists
- **WHEN** the rebuild-duckdb command is executed AND the output path already exists
- **THEN** the system SHALL exit with an error message without modifying the existing file

#### Scenario: Live database unaffected
- **WHEN** the rebuild is in progress
- **THEN** the live DuckDB database (`app/data/duckdb.db`) SHALL NOT be read, modified, or locked

### Requirement: Rebuild progress reporting
The system SHALL report progress during the rebuild including files processed, events loaded, and duration.

#### Scenario: Progress and summary output
- **WHEN** the rebuild completes
- **THEN** stdout SHALL show: files processed count, events loaded count, duplicates skipped count, corrupt lines skipped count, duration, and output file size

### Requirement: Memory-bounded processing
The system SHALL process archive files line-by-line with batch inserts, never loading entire files or the full archive into memory.

#### Scenario: Large archive directory processed without memory exhaustion
- **WHEN** the rebuild is executed against an archive directory containing hundreds of files totaling gigabytes
- **THEN** the process memory usage SHALL remain bounded (batch insert size of 1000 rows)

### Requirement: Mutual exclusion during rebuild
The system SHALL acquire the maintenance file lock during rebuild to prevent conflicts with batch loader writes.

#### Scenario: Lock acquired for rebuild
- **WHEN** the rebuild-duckdb command is executed AND the lock is available
- **THEN** the lock SHALL be held for the duration of the rebuild

#### Scenario: Lock unavailable
- **WHEN** the rebuild-duckdb command is executed AND another process holds the lock
- **THEN** the command SHALL exit with an error
