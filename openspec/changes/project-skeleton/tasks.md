## 1. Package Setup

- [x] 1.1 Create `pyproject.toml` with project metadata, production deps (fastapi, uvicorn[standard], pydantic-settings, pyjwt, httpx), dev deps (pytest, pytest-asyncio, httpx, ruff), and tool config (ruff, pytest)
- [x] 1.2 Create `app/__init__.py` (empty package marker)
- [x] 1.3 Create `app/middleware/__init__.py` (empty package marker)

## 2. Configuration

- [x] 2.1 Create `app/config.py` with `Settings(BaseSettings)`: DATABASE_PATH (default: `./atelier_marie.db`), JWT_SECRET (default: dev value), JWT_ALGORITHM (default: HS256), GOOGLE_CLIENT_ID (default: empty), GOOGLE_CLIENT_SECRET (default: empty), ADMIN_API_KEY (default: empty), ENVIRONMENT (default: development), SESSION_COOKIE_NAME (default: `session_id`), SESSION_MAX_AGE (default: 30 days in seconds)
- [x] 2.2 Add production validation: refuse to start if ENVIRONMENT=production and JWT_SECRET is the dev default

## 3. Database Layer

- [x] 3.1 Create `app/database.py` with `init_db(path)` that creates the database, sets WAL mode, enables foreign keys, and runs `CREATE TABLE IF NOT EXISTS` for all core tables (products, categories, cart_items, orders, order_items, sessions, users)
- [x] 3.2 Add `get_db()` context manager that yields a sqlite3 connection with WAL mode and foreign keys enabled, commits on success, rolls back on exception

## 4. Session Middleware

- [x] 4.1 Create `app/middleware/session.py` with `SessionMiddleware` class: reads session cookie, generates UUID v4 if missing, sets `request.state.session_id`, adds `Set-Cookie` on response (HTTPOnly, SameSite=Lax, 30-day max-age)

## 5. Application Factory

- [x] 5.1 Create `app/main.py` with `create_app()` function using lifespan context manager: calls `init_db()` on startup, adds session middleware, registers health router
- [x] 5.2 Add health router: `GET /v1/health` returns `{"status": "ok"}`
- [x] 5.3 Export `app = create_app()` at module level for `uvicorn app.main:app`

## 6. Test Infrastructure

- [x] 6.1 Create `conftest.py` with `db_path` fixture (tmp_path SQLite, schema initialized), `app` fixture (create_app with overridden config), and `client` fixture (httpx.AsyncClient with the test app)
- [x] 6.2 Create `tests/__init__.py`
- [x] 6.3 Create `tests/test_health.py` — verify `GET /v1/health` returns 200 with `{"status": "ok"}`
- [x] 6.4 Create `tests/test_session.py` — verify new visitor gets session cookie, existing session is preserved

## 7. Verification

- [x] 7.1 Run `pip install -e ".[dev]"` — confirm all deps install
- [x] 7.2 Run `uvicorn app.main:app` — confirm startup without errors
- [x] 7.3 Run `pytest` — all tests pass
- [x] 7.4 Run `ruff check .` — no lint errors
