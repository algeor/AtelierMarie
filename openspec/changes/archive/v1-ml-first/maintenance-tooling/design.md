## Context

AtelierMarie is a production e-commerce ML platform running on a single Oracle Free Tier VPS with 200GB storage. The system uses a dual-database architecture: SQLite for transactional data (users, products, orders) and DuckDB for the analytics/ML layer (events, session_identity, analytics tables). Processed event files are retained as JSONL archives for disaster recovery.

The application layer is fully deployed. What's missing are operational CLI tools for:
- Preventing unbounded storage growth (events accumulate ~10MB/day)
- Responding to GDPR requests (legally required within 30 days)
- Recovering from DuckDB corruption (single point of failure for analytics)
- Diagnosing production issues without spelunking through raw data

The platform processes personal data (user profiles, behavioral events) under EU GDPR jurisdiction, making data deletion and export capabilities a legal requirement rather than a nice-to-have.

## Goals / Non-Goals

**Goals:**
- Provide a complete CLI maintenance toolkit runnable via SSH or cron on the production VPS
- Enforce data retention policies to keep storage within the 200GB budget
- Enable GDPR compliance (right to erasure, right to data portability)
- Provide disaster recovery for the DuckDB analytics database
- Give operators a single-command system health overview
- Ensure all maintenance operations are safe to run alongside the live application

**Non-Goals:**
- Web UI or API endpoints for maintenance operations (admin-only, SSH access sufficient)
- Automated GDPR request handling (manual trigger by admin reviewing requests)
- Backup automation (handled separately by VPS-level snapshots)
- Real-time monitoring or alerting (out of scope — diagnose is point-in-time)
- Multi-VPS orchestration (single-server deployment)
- Retention policy configuration UI (hardcoded is fine for MVP)

## Decisions

### 1. CLI via `python -m app.maintenance` with argparse subcommands

**Choice**: Single package entry point with subcommands (`cleanup`, `delete-user`, `export-user`, `rebuild-duckdb`, `diagnose`, `vacuum`)

**Alternatives considered**:
- Separate scripts in `scripts/` directory → scattered, harder to share utilities (locks, DB connections)
- Click library → adds a dependency for minimal benefit over argparse
- Typer → same concern; argparse is stdlib and sufficient

**Rationale**: A single package keeps shared utilities (lock management, DB access helpers) in `__init__.py`, and `python -m` invocation is natural for Python projects. Argparse is stdlib — zero new dependencies.

### 2. File-based mutual exclusion via `fcntl.flock()`

**Choice**: Maintenance operations acquire `app/data/.batch.lock` using Python's `fcntl.flock(LOCK_EX | LOCK_NB)`. This is the single unified lock that guards all DuckDB writes — including the event batch loader, session expiry flush, and analytics compute job.

**Alternatives considered**:
- PID file with stale-PID detection → race conditions, doesn't prevent concurrent DuckDB writers
- Database-level locking → DuckDB doesn't support multi-process locking natively
- systemd oneshot + conflicts → too coupled to deployment mechanism

**Rationale**: All DuckDB writers coordinate through `.batch.lock`. Maintenance operations need exclusive DuckDB access, so they acquire the same lock. Non-blocking acquisition means maintenance tools fail fast if another writer holds the lock, rather than deadlocking.

### 3. GDPR deletion uses NULL-ification rather than cascading deletes

**Choice**: Orders and session_identity rows are anonymized (user_id set to NULL) rather than deleted.

**Alternatives considered**:
- CASCADE DELETE orders → loses business data (revenue history, inventory reconciliation)
- Soft-delete with encryption → complex, storage still consumed, key management burden

**Rationale**: GDPR requires erasure of personal data, not destruction of business records. An order with `user_id=NULL` contains no personal data — it's just a sales record. Similarly, session_identity with `user_id=NULL` becomes anonymous behavioral data. Events already only reference session_id, so breaking the session→user link achieves full anonymization.

### 4. DuckDB rebuild writes to a new file, never modifies live

**Choice**: `rebuild_duckdb` creates a new database file at a user-specified path. The operator must manually swap files after verification.

**Alternatives considered**:
- In-place rebuild with backup → risk of data loss if rebuild fails mid-way
- Atomic rename after automated verification → verification criteria unclear, too risky to automate

**Rationale**: The rebuild is a disaster recovery tool. The operator needs to verify row counts, check for anomalies, and only then consciously swap the file. Automation here introduces risk for minimal convenience benefit.

**Note:** After rebuilding the events table from the JSONL archive, the `rebuild-duckdb` command should trigger an analytics recompute to regenerate the `analytics_*` tables (session metrics, funnel stages, etc.) that are derived from events. Without this step, the rebuilt database would be missing all computed analytics data.

### 5. Streaming file processing for archive rebuild

**Choice**: Process JSONL archive files one at a time, line by line. Never load the full archive into memory.

**Alternatives considered**:
- DuckDB's native `read_json_auto()` on glob → memory-efficient for DuckDB but doesn't handle our dedup/corrupt-line logic
- Batch loading all files into a temp table then dedup → requires 2x storage

**Rationale**: The archive could grow to hundreds of GB. Line-by-line processing with batch INSERT (1000 rows at a time) keeps memory bounded regardless of archive size, while leveraging DuckDB's INSERT OR IGNORE for deduplication.

### 6. Diagnostics reads process table for service status

**Choice**: Use `psutil` (already likely available) or parse `/proc` directly to check if API and batch loader processes are running.

**Alternatives considered**:
- systemd status queries → couples to deployment mechanism
- Health check HTTP endpoints → requires API to be running (circular)
- PID files → stale PID problem

**Rationale**: Direct process inspection works regardless of how services were started. If systemd is available, we can augment, but the base case should work with any process manager. Fall back to checking PID files or known process patterns if psutil isn't available.

## Risks / Trade-offs

**[File lock contention]** → Maintenance operations will fail if the batch loader, session expiry, or analytics compute holds `.batch.lock`. **Mitigation**: Schedule cleanup at 3am when batch activity is lowest. Lock acquisition has a short timeout (5s) with a clear error message suggesting retry.

**[GDPR deletion is irreversible]** → Once session_identity is unlinked, there's no way to re-associate events with a user. **Mitigation**: Require `--confirm` flag, show a preview of what will be deleted, log everything to `deletion_log.jsonl` for audit purposes.

**[DuckDB rebuild duration]** → Rebuilding from months of archives could take minutes to hours. **Mitigation**: Show progress (files processed, events loaded) during rebuild. The new file approach means the live system is unaffected during rebuild.

**[Disk space during rebuild]** → Temporarily two copies of DuckDB exist. **Mitigation**: Diagnose command shows free disk space. Document that 2x DuckDB size in free space is required before starting a rebuild.

**[Archive file corruption]** → JSONL files could have corrupt lines from interrupted writes. **Mitigation**: Skip unparseable lines with a warning log (same behavior as the batch loader). Report corruption count at end.

**[Single-server lock coordination]** → File locks only work on a single machine. **Mitigation**: This is explicitly a single-VPS deployment. If multi-server is ever needed, the lock mechanism would need to be replaced with distributed locking — but that's a non-goal.
