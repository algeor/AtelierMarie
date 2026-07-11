## 1. Package Structure & Shared Utilities

- [ ] 1.1 Create `app/maintenance/__init__.py` with shared utilities: file lock context manager (`acquire_lock`), DuckDB connection helper, SQLite connection helper, timestamped logging helper
- [ ] 1.2 Create `app/maintenance/__main__.py` with argparse subcommand dispatcher routing to cleanup, delete-user, export-user, rebuild-duckdb, diagnose, and vacuum commands

## 2. Data Retention Cleanup

- [ ] 2.1 Implement `app/maintenance/cleanup.py` — archive file cleanup (delete `.done` files older than 30 days from `app/data/events/archive/`)
- [ ] 2.2 Add DuckDB events cleanup (DELETE WHERE server_timestamp < now() - 90 days)
- [ ] 2.3 Add DuckDB session_identity cleanup (DELETE WHERE last_seen < now() - 90 days AND is_expired = TRUE)
- [ ] 2.4 Add `--dry-run` flag support showing what would be deleted without making changes
- [ ] 2.5 Add file lock acquisition and summary logging output

## 3. GDPR User Deletion

- [ ] 3.1 Implement `app/maintenance/delete_user.py` — parse `--user-id` and `--confirm` arguments, verify user exists
- [ ] 3.2 Implement deletion logic: DELETE from SQLite users, SET user_id=NULL on orders, SET user_id=NULL on session_identity
- [ ] 3.3 Add preview mode (no `--confirm`): show what would be affected without making changes
- [ ] 3.4 Add audit log append to `app/data/deletion_log.jsonl` with user_id, timestamp, and affected row counts

## 4. GDPR User Data Export

- [ ] 4.1 Implement `app/maintenance/export_user.py` — parse `--user-id` and `--output` arguments, verify user exists
- [ ] 4.2 Gather user profile from SQLite, sessions from DuckDB session_identity, events across all sessions, and orders with items
- [ ] 4.3 Write complete JSON export file and print summary (record counts, file size)

## 5. DuckDB Rebuild from Archive

- [ ] 5.1 Implement `app/maintenance/rebuild_duckdb.py` — parse `--archive-dir` and `--output` arguments, validate output path doesn't exist
- [ ] 5.2 Create fresh DuckDB with events table schema and indexes
- [ ] 5.3 Implement streaming line-by-line file processing with batch INSERT (1000 rows), sorted by filename, handling corrupt lines
- [ ] 5.4 Add deduplication via INSERT OR IGNORE and progress/summary reporting (files, events, duplicates, corrupt lines, duration)

## 6. System Diagnostics

- [ ] 6.1 Implement `app/maintenance/diagnose.py` — storage diagnostics (buffer files, archive count/size, DuckDB size, SQLite size, disk free)
- [ ] 6.2 Add DuckDB diagnostics (total events, latest event timestamp, active/expired session counts)
- [ ] 6.3 Add SQLite diagnostics (users, active/inactive products, orders)
- [ ] 6.4 Add service status checks (API, batch loader, ML compute, session expiry — via process inspection)
- [ ] 6.5 Add issue detection logic (buffer file accumulation, stale event pipeline) with warning/OK indicators

## 7. Vacuum & Optimize

- [ ] 7.1 Implement `app/maintenance/vacuum.py` — VACUUM and ANALYZE DuckDB, VACUUM SQLite
- [ ] 7.2 Add size-before/size-after reporting for each database

## 8. Testing & Validation

- [ ] 8.1 Add unit tests for shared utilities (lock acquisition, connection helpers)
- [ ] 8.2 Add integration tests for cleanup (with temp archive files and test DuckDB)
- [ ] 8.3 Add integration tests for GDPR deletion and export (with seeded test data)
- [ ] 8.4 Add integration tests for rebuild (with sample archive files, including corrupt lines)
- [ ] 8.5 Validate all commands via `python -m app.maintenance --help` and subcommand `--help`
