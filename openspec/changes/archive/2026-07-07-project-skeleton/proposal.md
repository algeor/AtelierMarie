## Why

The core-ecommerce spec defines what the system does, but there's no runnable project yet — no package management, no app entry point, no database setup, no test infrastructure. Without this skeleton, nothing in core-ecommerce can be built or tested. This is the prerequisite for all implementation work.

## What Changes

- Add `pyproject.toml` with production and dev dependencies
- Create `app/` package with `__init__.py`
- Create `app/config.py` using pydantic-settings for all env-driven configuration
- Create `app/database.py` with SQLite connection management and WAL mode setup
- Create `app/main.py` with FastAPI app factory, lifespan handler, and router registration
- Create `app/middleware/session.py` with session cookie middleware stub
- Create `conftest.py` with test database fixture (isolated per-test SQLite)

## Capabilities

### New Capabilities
- `project-foundation`: Package setup, configuration, database connection, app factory, and test infrastructure

### Modified Capabilities
<!-- None — this is greenfield scaffolding -->

## Impact

- **Dependencies:** Introduces fastapi, uvicorn, pydantic-settings, pyjwt, httpx; dev deps: pytest, pytest-asyncio, ruff
- **Code:** Creates `app/` package structure from scratch
- **APIs:** Registers health endpoint (`GET /v1/health`) — no business routes yet
- **Systems:** Enables `uvicorn app.main:app --reload` and `pytest` to run successfully
