## Why

The test suite (294 tests) is unacceptably slow because every test function spins up a fresh `init_db()` + `create_app()` + real `SessionMiddleware` DB round-trip. The session middleware alone adds a sqlite3 connect → INSERT/SELECT → commit on **every HTTP request in every route test**. With function-scoped fixtures and duplicated setup across 18 files, the overhead dominates actual test logic.

## What Changes

- Introduce a **no-op session middleware** for route tests that stamps `request.state.session_id` without touching the database or parsing cookies.
- Lift the `app` and `client` fixtures to **module scope** so `init_db()` and `create_app()` run once per file, not once per test.
- Consolidate duplicated fixtures (`admin_app`, `admin_client`, product seeding, session creation) into shared `conftest.py` helpers.
- Add a `make_session()` helper that replaces the 6-line INSERT pattern repeated in 8+ files.
- Service-layer tests get a **module-scoped DB connection** with per-test cleanup (DELETE FROM tables) instead of per-test `init_db()`.
- `test_session.py` and `test_session_hardened.py` remain unchanged — they test real middleware behavior with function-scoped fixtures.

## Capabilities

### New Capabilities
- `test-fixtures`: Shared test infrastructure — module-scoped app/DB fixtures, mock session middleware, reusable seed helpers, and consolidated admin/client factories.

### Modified Capabilities
<!-- No spec-level behavior changes — this is purely internal test infrastructure. -->

## Impact

- **Files changed:** `conftest.py` (major rewrite), all 16 test files except `test_session.py` / `test_session_hardened.py` (fixture swap + cleanup of inline setup).
- **No production code changes.** No API or behavior differences.
- **Dependencies:** None new. Uses existing `pytest`, `pytest-xdist`, `httpx`.
- **Risk:** Module-scoped fixtures mean tests within a file share DB state — requires per-test cleanup (DELETE) or careful ordering. Mitigated by explicit cleanup fixtures.
