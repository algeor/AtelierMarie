## ADDED Requirements

### Requirement: Daily automated backup of SQLite
The backup script SHALL create a consistent backup of the SQLite database daily.

#### Scenario: Backup created successfully
- **WHEN** the backup cron runs at 3:00 AM
- **THEN** a point-in-time consistent copy of `sqlite.db` is created at `/opt/atelier/backups/sqlite-YYYY-MM-DD.db`
- **AND** the backup is created using SQLite's `.backup` command (safe during concurrent writes)

### Requirement: Daily automated backup of DuckDB
The backup script SHALL create a consistent backup of the DuckDB database daily.

#### Scenario: DuckDB backed up with lock
- **WHEN** the backup script runs
- **THEN** it acquires the `.batch.lock` file lock (preventing concurrent batch loader writes)
- **AND** copies `duckdb.db` to `/opt/atelier/backups/duckdb-YYYY-MM-DD.db`
- **AND** releases the lock after copy completes

#### Scenario: Lock unavailable (batch in progress)
- **WHEN** the backup script cannot acquire the lock within 60 seconds
- **THEN** it logs a warning and retries after 60 seconds (up to 3 attempts)

### Requirement: Backup retention of 7 days
The backup script SHALL retain only the last 7 days of backups and delete older ones.

#### Scenario: Old backups deleted
- **WHEN** the backup script completes
- **THEN** backup files older than 7 days are deleted from `/opt/atelier/backups/`

#### Scenario: At least one backup always retained
- **WHEN** the retention cleanup runs
- **THEN** the most recent backup is never deleted, even if it's older than 7 days (safety net)

### Requirement: Backup script reports results
The backup script SHALL output a summary of actions taken.

#### Scenario: Successful backup logged
- **WHEN** the backup completes successfully
- **THEN** it logs: files created, sizes, old files deleted, duration

#### Scenario: Backup failure logged
- **WHEN** the backup fails (disk full, lock timeout, etc.)
- **THEN** it logs the error with enough detail to diagnose and exits with non-zero code

### Requirement: DuckDB rebuildable from archive
In the event of DuckDB corruption, the database SHALL be fully rebuildable from archived JSONL files.

#### Scenario: Disaster recovery rebuild
- **WHEN** `python -m app.maintenance.rebuild_duckdb` is run against the JSONL archive
- **THEN** a new DuckDB database is created containing all events from the archive files
- **AND** the rebuild handles duplicate event_ids (INSERT OR IGNORE)

### Requirement: Restore documentation
The backup system SHALL include documentation explaining how to restore from backup.

#### Scenario: Restore procedure documented
- **WHEN** an operator needs to restore the system
- **THEN** `deploy/RESTORE.md` provides step-by-step instructions for: stopping services, replacing database files, restarting services, and verifying restoration
