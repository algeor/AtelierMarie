## Context

The test suite has 294 tests across 18 files. Every test function currently:
1. Gets a fresh `tmp_path` → new SQLite file
2. Calls `init_db()` → full DDL (6 tables, 8 indexes, 5 triggers, FTS5 virtual table)
3. Calls `create_app()` → new FastAPI app instance
4. For route tests: the real `SessionMiddleware` opens a DB connection and inserts/queries session rows on every HTTP request

With `pytest-xdist -n auto` already enabled, the bottleneck is per-test fixture overhead, not parallelism. Profiling shows `init_db()` + `create_app()` dominate — actual test logic is fast.

Duplicated fixtures across files (`admin_app`/`admin_client` copy-pasted in 3 files, product seeding done 8 different ways, session INSERT repeated in 6+ places) prevent any consolidation.

## Goals / Non-Goals

**Goals:**
- Reduce test wall-clock time by ~10× via module-scoped fixtures and mocked middleware
- Consolidate duplicated fixture code into shared `conftest.py`
- Maintain full test isolation (no test-order dependencies, no cross-test data leakage)
- Keep session middleware tests (`test_session.py`, `test_session_hardened.py`) testing real behavior

**Non-Goals:**
- Changing production code
- Reducing test count or coverage
- Switching test frameworks (staying with pytest + httpx)
- Optimizing `test_models.py` (already pure Pydantic, no I/O)

## Decisions

### Decision 1: Mock Session Middleware for Route Tests

**Choice:** Replace `SessionMiddleware` with a no-op `FakeSessionMiddleware` in all route test fixtures except session-specific tests.

**Rationale:** The real middleware does a full DB round-trip (connect → SELECT/INSERT → commit → close) on every request. In route tests, we don't care about session creation logic — we care about route/service behavior. The middleware is thoroughly tested in its own files.

**Implementation:**
```python
class FakeSessionMiddleware(BaseHTTPMiddleware):
    """Stamps a fixed session_id without DB or cookie logic."""
    def __init__(self, app, session_id: str):
        super().__init__(app)
        self._session_id = session_id

    async def dispatch(self, request, call_next):
        request.state.session_id = self._session_id
        request.state.session_is_new = False
        return await call_next(request)
```

The app factory must allow middleware substitution. Approach: after `create_app()`, replace the middleware stack entry. FastAPI stores middleware as a list — we can pop the real one and add the fake.

**Alternative considered:** Monkeypatching `get_db()` inside the middleware to return a no-op. Rejected: fragile, still has overhead of the middleware logic running.

### Decision 2: Module-Scoped App Fixture with Per-Test Cleanup

**Choice:** `scope="module"` for `app`, `client`, and `db` fixtures. Each test cleans up via `DELETE FROM` at teardown.

**Rationale:** `init_db()` + `create_app()` runs once per file (~18 times total) instead of once per test (294 times). Isolation is maintained by deleting rows between tests.

**Cleanup strategy:**
```python
@pytest.fixture(autouse=True)
def _clean_tables(db):
    """Delete all data between tests (module-scoped DB persists)."""
    yield
    for table in ("order_items", "orders", "cart_items", "sessions", "products"):
        db.execute(f"DELETE FROM {table}")
    db.commit()
```

Tables deleted in FK-safe order (children first). FTS5 stays in sync via existing DELETE triggers.

**Alternative considered:** SAVEPOINT/ROLLBACK wrapping each test. Rejected: impossible because `get_db()` creates new connections that auto-commit — can't wrap external connections in a single transaction.

### Decision 3: Shared Seed Helpers (Not Fixtures)

**Choice:** Provide helper functions (`make_session()`, `seed_products()`, `make_admin_client()`) rather than more fixtures.

**Rationale:** Helpers are explicit — tests call what they need. Avoids the pytest fixture graph becoming a hidden dependency maze. Tests read top-to-bottom.

```python
# conftest.py
def make_session(conn, session_id="test-session") -> str:
    """Insert a session row and return its ID."""
    ...

def seed_products(conn, products=DEFAULT_PRODUCTS) -> None:
    """Insert product rows from a list of dicts."""
    ...
```

**Alternative considered:** Parametrized fixtures with `@pytest.fixture(params=[...])`. Rejected: makes test output noisy and doesn't solve the "8 different seeding approaches" problem.

### Decision 4: Separate Fixture Scoping for Service vs Route Tests

**Choice:**
- **Service tests** (`test_*_service.py`): Module-scoped raw `sqlite3.Connection`. No app, no client, no middleware.
- **Route tests** (`test_*_routes.py`): Module-scoped app + mock middleware + module-scoped `AsyncClient`.
- **Session tests** (`test_session*.py`): Function-scoped everything (real middleware). Unchanged.

**Rationale:** Service tests don't need HTTP infrastructure at all. Route tests need it but don't need real session logic. Session tests need everything real.

### Decision 5: `monkeypatch` Replacement for Module Scope

**Choice:** Use `monkeypatch_module` (a module-scoped monkeypatch fixture via `pytest.MonkeyPatch` context manager) since the built-in `monkeypatch` is function-scoped only.

```python
@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()
```

## Risks / Trade-offs

**[Test-order coupling]** → Mitigated by autouse `_clean_tables` fixture that runs after every test. If a test fails mid-way and doesn't clean up, the `yield`-based fixture still executes cleanup.

**[FTS5 desync on DELETE]** → Mitigated: existing `products_fts_delete` trigger fires on DELETE, keeping FTS in sync.

**[Harder debugging of individual tests]** → Mitigated: `pytest --forked -k test_name` still works for isolation. Module scope doesn't prevent running single tests.

**[xdist interaction]** → Non-issue: xdist distributes by module. Each worker gets its own module-scoped fixtures independently. No cross-worker sharing.

**[Middleware mock drift]** → Risk that real middleware changes break route tests silently. Mitigated: `test_session*.py` still tests real middleware. Any middleware regression shows up there.
