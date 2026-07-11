## Why

The AtelierMarie platform is event-first: every ML feature (recommendations, ranking, analytics, conversion tracking) depends on a reliable stream of user behavior events. Currently the project is a bare FastAPI hello-world with no event capture, no storage pipeline, and no path to ML. Without a robust, crash-safe ingestion pipeline with clear concurrency semantics, nothing else can be built.

The system must work on zero-budget free-tier infrastructure (no Kafka, no Redis, no managed queues), survive crashes without data loss, and scale from a single worker to multiple workers without architectural redesign.

## What Changes

- Add a `POST /v1/events` endpoint accepting single events or batches (up to 1000 per request)
- Implement Pydantic event models with server-side enrichment (event_id generation, server_timestamp)
- Create a thread-safe JSONL writer that appends events to date-partitioned buffer files
- Build a background batch loader that periodically bulk-inserts buffered JSONL into DuckDB with deduplication
- Set up DuckDB schema (events table with indexes) and read-only connection management
- Add a `GET /health` endpoint exposing buffer status and pipeline health
- Wire everything together via FastAPI lifespan (startup: init DB + start loader; shutdown: flush + close)
- Introduce project configuration via pydantic-settings (paths, intervals, limits)
- Add unit and integration test suite covering models, writer, loader, and full API flow

## Capabilities

### New Capabilities

- `event-collection`: HTTP API for ingesting behavioral events (single and batch), with validation, enrichment, and 202 Accepted semantics
- `event-buffering`: Thread-safe, crash-safe JSONL file writer with date-partitioned buffer files and O_APPEND atomicity
- `event-loading`: Periodic batch loader that bulk-inserts JSONL into DuckDB with deduplication, transaction-per-file safety, and automatic archival
- `pipeline-health`: Health check endpoint exposing buffer file count, last batch time, and DuckDB connectivity

### Modified Capabilities

<!-- No existing capabilities to modify — this is the first feature on a fresh project -->

## Impact

- **New dependencies**: duckdb, pydantic-settings
- **New directory structure**: `app/` package with api, models, ingestion, db, and data subdirectories
- **main.py**: Replaced with import from app factory
- **Disk**: Creates `app/data/events/buffer/` and `app/data/events/archive/` at runtime
- **Port 8000**: API contract established at `/v1/events` and `/health`
- **Background process**: asyncio task running in the FastAPI event loop (single-worker); future multi-worker will extract to separate process
