## 1. Project Foundation

- [ ] 1.1 Create `requirements.txt` with fastapi, uvicorn[standard], pydantic, pydantic-settings, duckdb
- [ ] 1.2 Create `app/config.py` with Settings class (data_dir, buffer_dir, archive_dir, duckdb_path, batch_interval_seconds, max_event_size_bytes)
- [ ] 1.3 Create package init files: `app/__init__.py`, `app/api/__init__.py`, `app/api/v1/__init__.py`, `app/models/__init__.py`, `app/ingestion/__init__.py`, `app/db/__init__.py`

## 2. Event Models

- [ ] 2.1 Create `app/models/events.py` with EventType enum (page_view, product_view, search, click, add_to_cart, remove_from_cart, purchase, impression, session_start, session_end)
- [ ] 2.2 Add EventIn model (client input: optional event_id, required session_id, nullable user_id, event_type, optional product_id, optional timestamp, metadata dict)
- [ ] 2.3 Add Event model (canonical: generated event_id, server_timestamp, all fields)
- [ ] 2.4 Add EventBatchIn model (events array, min_length=1, max_length=1000)
- [ ] 2.5 Add EventResponse model (accepted count, event_ids list)

## 3. Storage Layer

- [ ] 3.1 Create `app/db/schema.py` with init_db() — CREATE TABLE IF NOT EXISTS events (event_id VARCHAR PK, session_id, user_id, event_type, product_id, server_timestamp TIMESTAMPTZ, metadata JSON) + indexes
- [ ] 3.2 Create `app/db/engine.py` with get_read_connection() returning read_only=True DuckDB connection

## 4. JSONL Writer

- [ ] 4.1 Create `app/ingestion/writer.py` with JSONLWriter class — date-partitioned file naming, O_APPEND open mode, line-buffered
- [ ] 4.2 Implement write_event() and write_batch() methods with max size check
- [ ] 4.3 Implement file handle caching per date partition with thread-safe dict access
- [ ] 4.4 Implement flush() and close() methods for graceful shutdown
- [ ] 4.5 Create module-level singleton instance

## 5. Batch Loader

- [ ] 5.1 Create `app/ingestion/loader.py` with BatchLoader class
- [ ] 5.2 Implement get_pending_files() — glob buffer/*.jsonl, sorted by name
- [ ] 5.3 Implement load_file() — read_json with explicit column types, staging table, INSERT OR IGNORE, transaction per file, archive on success
- [ ] 5.4 Implement run_batch() — iterate pending files, aggregate results, catch per-file errors
- [ ] 5.5 Implement _archive_file() — rename to archive/ with .done suffix

## 6. Background Scheduler

- [ ] 6.1 Create `app/ingestion/scheduler.py` with batch_loader_loop() async function
- [ ] 6.2 Implement sleep loop with configurable interval
- [ ] 6.3 Implement file lock acquisition (fcntl.flock, LOCK_EX | LOCK_NB on app/data/.batch.lock) — skip cycle if lock unavailable
- [ ] 6.4 Use run_in_executor for blocking DuckDB operations (while holding lock)
- [ ] 6.5 Flush writer before each batch cycle
- [ ] 6.6 Release file lock after batch completes (or on error)

## 7. API Endpoint

- [ ] 7.1 Create `app/api/v1/events.py` with APIRouter (prefix=/v1)
- [ ] 7.2 Implement POST /v1/events — detect single vs batch payload, validate, enrich, write
- [ ] 7.3 Implement _enrich_event() — generate event_id if missing, set server_timestamp, move client timestamp to metadata
- [ ] 7.4 Handle errors: 413 for oversized events, 503 for storage failures

## 8. Health Endpoint

- [ ] 8.1 Add GET /health to app — report status, buffer_files count, last_batch_at, duckdb_total_events
- [ ] 8.2 Implement degraded status detection (DuckDB unreachable, buffer unwritable)

## 9. App Wiring

- [ ] 9.1 Create `app/__init__.py` with create_app() factory and asynccontextmanager lifespan
- [ ] 9.2 Wire lifespan startup: create directories, init_db(), start batch_loader_loop task
- [ ] 9.3 Wire lifespan shutdown: cancel loader task, flush writer, close writer
- [ ] 9.4 Include events router and health endpoint
- [ ] 9.5 Update root `main.py` to import app from package

## 10. Tests

- [ ] 10.1 Create `tests/conftest.py` with tmp_path fixtures for isolated buffer/archive/duckdb
- [ ] 10.2 Create `tests/test_models.py` — valid/invalid events, enrichment, batch limits, enum validation
- [ ] 10.3 Create `tests/test_writer.py` — file creation, content validity, concurrent writes, oversized rejection, flush/close
- [ ] 10.4 Create `tests/test_loader.py` — successful load, dedup, corrupt lines skipped, rollback on error, archive behavior
- [ ] 10.5 Create `tests/test_api_events.py` — single event 202, batch 202, invalid 422, full pipeline integration
