## Context

AtelierMarie has a planning-phase codebase: ARCHITECTURE.md, IMPLEMENTATION_PLAN.md, and openspec changes define the system, but `app/` only contains a stub `main.py`. There's no dependency management, no configuration system, no database layer, and no test infrastructure. The core-ecommerce change (products, cart, checkout, orders, auth, admin) cannot be implemented until these foundations exist.

The target deployment is a single VPS (Oracle Cloud Free Tier) running Uvicorn behind Nginx. SQLite in WAL mode is the only production database. The stack is Python 3.11 + FastAPI + Pydantic 2.

## Goals / Non-Goals

**Goals:**
- Runnable `uvicorn app.main:app --reload` that starts cleanly and serves a health endpoint
- `pytest` runs successfully with an isolated test database per test
- Configuration driven by environment variables with sensible development defaults
- SQLite connection with WAL mode, foreign keys enabled, and schema initialization on startup
- App factory pattern that supports clean testing and lifespan management
- Session middleware stub ready for cart/auth to build on

**Non-Goals:**
- Business routes (products, cart, orders) — those belong to core-ecommerce
- Frontend setup — Next.js is a separate app
- Deployment configuration (Nginx, systemd) — that's a separate change
- Analytics/ML infrastructure (Layer 2) — deferred
- Production secrets management — dev defaults are sufficient for now

## Decisions

### 1. `pyproject.toml` over `requirements.txt`

**Choice:** Use `pyproject.toml` with `[project.optional-dependencies]` for dev deps.

**Rationale:** Standard Python packaging (PEP 621). Single source of truth for metadata, dependencies, and tool config (ruff, pytest). Pip can install directly: `pip install -e ".[dev]"`.

**Alternatives considered:**
- `requirements.txt` + `requirements-dev.txt`: No metadata, no tool config, two files to maintain.
- Poetry/PDM: Adds a tool dependency for a single-developer project. Overkill.

### 2. pydantic-settings for configuration

**Choice:** Single `app/config.py` using `pydantic_settings.BaseSettings` with env vars and `.env` file support.

**Rationale:** Type-safe, validates on startup (fail-fast), auto-documents all config, integrates with FastAPI's dependency injection. Secrets come from env vars in production; `.env` file for local dev.

**Alternatives considered:**
- `os.environ` with manual parsing: No validation, no defaults documentation.
- `python-dotenv` alone: No type safety, no structured access.

### 3. SQLite connection via contextmanager (no ORM)

**Choice:** Raw `sqlite3` with a `get_db()` context manager yielding connections. WAL mode + foreign keys set on each connection open. Schema initialized via `CREATE TABLE IF NOT EXISTS` on startup.

**Rationale:** SQLite + raw SQL is the simplest reliable approach for a single-server app. ORMs (SQLAlchemy, Tortoise) add complexity and abstraction for a 6-table schema. The team (one developer) reads SQL fluently.

**Alternatives considered:**
- SQLAlchemy Core: Unnecessary abstraction layer for a single-file database.
- aiosqlite: Async wrappers around SQLite add complexity with minimal benefit — SQLite operations are sub-millisecond for this data volume.

### 4. App factory pattern with lifespan

**Choice:** `create_app()` function in `app/main.py` using FastAPI's lifespan context manager for startup/shutdown (DB init, connection pool).

**Rationale:** Testable (each test can create a fresh app), supports resource cleanup, follows FastAPI best practices.

### 5. Session middleware as cookie-based UUID

**Choice:** Custom middleware that reads/sets a session cookie (UUID v4, HTTPOnly, SameSite=Lax). Stores session ID on `request.state.session_id`.

**Rationale:** Anonymous-first cart requires session identity before auth. Lightweight (no server-side session storage in this layer — cart data lives in SQLite keyed by session ID).

### 6. Test isolation via tmp_path SQLite

**Choice:** `conftest.py` provides a `db` fixture that creates a fresh SQLite database in `tmp_path`, runs schema init, and yields the path. Tests use dependency override to inject it.

**Rationale:** Each test gets its own database — no test pollution, no cleanup required, runs in parallel.

## Risks / Trade-offs

- **[Synchronous SQLite in async framework]** → For this data volume (<10k products, <1k concurrent users), SQLite operations complete in <1ms. If needed later, wrap in `run_in_executor`. Not worth the complexity now.
- **[No ORM means manual schema migrations]** → Mitigated by simple schema (6 tables). Future: add a `schema_version` table and migration scripts if schema evolves significantly.
- **[Single connection pattern]** → SQLite handles concurrency via WAL mode. If write contention appears under load, add a write lock or queue. Unlikely at this scale.
