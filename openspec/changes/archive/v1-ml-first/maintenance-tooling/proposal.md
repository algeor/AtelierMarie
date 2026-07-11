## Why

AtelierMarie's application layer (API, event pipeline, ML compute) is fully deployed, but there are no operational tools for day-to-day system maintenance. Without these, the platform will accumulate unbounded data (events, archive files), cannot respond to GDPR requests (deletion, export), has no disaster recovery path if DuckDB corrupts, and offers no visibility into system health. These are table-stakes operational requirements for running a production e-commerce system handling personal data under EU regulations.

## What Changes

- Add a `app/maintenance/` CLI module with six operational commands accessible via `python -m app.maintenance <command>`
- **Data retention enforcement** — automated cleanup of JSONL archive files (30-day), DuckDB events and expired sessions (90-day)
- **GDPR deletion** — complete user erasure across SQLite and DuckDB, with audit logging
- **GDPR data export** — full user data portability export as JSON
- **DuckDB rebuild** — disaster recovery tool to reconstruct the analytics database from archived JSONL files
- **System diagnostics** — single-command health check reporting storage, database stats, and service status
- **Vacuum & optimize** — periodic database compaction for both DuckDB and SQLite
- All commands use file-based mutual exclusion to prevent conflicts with the running batch loader and ML compute jobs
- All destructive operations require explicit `--confirm` flags and support `--dry-run` mode

## Capabilities

### New Capabilities

- `data-retention`: Automated cleanup of expired data across JSONL archive, DuckDB events, and DuckDB session_identity tables based on configurable retention periods
- `gdpr-deletion`: Complete user data erasure across all storage layers (SQLite users, orders anonymization, DuckDB session unlinking) with append-only audit log
- `gdpr-export`: User data portability export aggregating profile, sessions, events, and orders into a single JSON file
- `disaster-recovery`: DuckDB rebuild from archived JSONL files — creates a fresh database without touching the live one
- `system-diagnostics`: Single-command health check covering storage usage, database statistics, service status, and anomaly detection
- `database-optimization`: Periodic VACUUM and ANALYZE operations for DuckDB and SQLite to reclaim space and update query optimizer statistics

### Modified Capabilities

_(none — this change introduces new CLI tooling without modifying existing application behavior)_

## Impact

- **New code**: `app/maintenance/` package (7 files: `__init__.py`, `__main__.py`, `cleanup.py`, `delete_user.py`, `export_user.py`, `rebuild_duckdb.py`, `diagnose.py`, `vacuum.py`)
- **Dependencies**: None new (uses `argparse` from stdlib)
- **Database access**: Reads and writes to both SQLite (`app/data/atelier.db`) and DuckDB (`app/data/duckdb.db`); must coordinate with existing batch loader and ML compute via file locks
- **File system**: Creates/manages `app/data/.maintenance.lock` and `app/data/deletion_log.jsonl`
- **Deployment**: New cron entries for daily cleanup (3am) and weekly vacuum; scripts run on the Oracle Free Tier VPS via SSH
- **Existing services**: No changes to the FastAPI application, event pipeline, or ML compute — maintenance tools operate alongside them using file-lock coordination
