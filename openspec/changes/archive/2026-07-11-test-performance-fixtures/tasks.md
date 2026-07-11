## 1. Core Infrastructure in conftest.py

- [ ] 1.1 Add `monkeypatch_module` fixture (module-scoped `pytest.MonkeyPatch`)
- [ ] 1.2 Add `FakeSessionMiddleware` class that stamps `request.state.session_id` without DB
- [ ] 1.3 Rewrite `app` fixture to module scope with `tmp_path_factory` and `FakeSessionMiddleware`
- [ ] 1.4 Add `_clean_tables` autouse function-scoped fixture (DELETE in FK-safe order after each test)
- [ ] 1.5 Rewrite `client` fixture to module scope (shares module-scoped app)
- [ ] 1.6 Rewrite `db` fixture to module scope (raw connection to module-scoped DB file)

## 2. Shared Helpers in conftest.py

- [ ] 2.1 Add `make_session(conn, session_id=None)` helper function
- [ ] 2.2 Add `seed_products(conn, products=None)` helper with DEFAULT_PRODUCTS list
- [ ] 2.3 Add module-scoped `admin_client` fixture (AsyncClient with Bearer auth header)
- [ ] 2.4 Add module-scoped `service_db` fixture for service-layer tests (raw connection, no app)

## 3. Migrate Service Tests

- [ ] 3.1 Refactor `test_product_service.py` — use `service_db` + `seed_products()` + `_clean_tables`
- [ ] 3.2 Refactor `test_cart_service.py` — replace `cart_db` with `service_db` + helpers
- [ ] 3.3 Refactor `test_order_service.py` — replace local `conn` fixture with `service_db` + helpers

## 4. Migrate Route Tests

- [ ] 4.1 Refactor `test_product_routes.py` — use module-scoped `app`/`client`, remove local `_products` fixture
- [ ] 4.2 Refactor `test_cart_routes.py` — use module-scoped `client`, replace `_seed_products` with `seed_products()`
- [ ] 4.3 Refactor `test_order_routes.py` — remove `order_app`/`order_client`/`order_session_id`, use shared fixtures + helpers
- [ ] 4.4 Refactor `test_admin_routes.py` — remove local `admin_app`/`admin_client`, use shared `admin_client`
- [ ] 4.5 Refactor `test_day6_admin_dashboard.py` — remove duplicated `admin_app`/`admin_client`, use shared fixtures
- [ ] 4.6 Refactor `test_integration.py` — use module-scoped fixtures + helpers
- [ ] 4.7 Refactor `test_routers.py` — use module-scoped `client`

## 5. Migrate Remaining Tests

- [ ] 5.1 Refactor `test_database.py` — use `service_db` fixture
- [ ] 5.2 Refactor `test_database_constraints.py` — use `service_db` fixture
- [ ] 5.3 Refactor `test_auth.py` — use module-scoped app + helpers for user/session setup
- [ ] 5.4 Refactor `test_health.py` — use module-scoped `client`
- [ ] 5.5 Refactor `test_lifespan.py` — keep function-scoped (tests app startup/shutdown directly)

## 6. Preserve Session Tests (No Changes)

- [ ] 6.1 Verify `test_session.py` still uses function-scoped real middleware (add comment header)
- [ ] 6.2 Verify `test_session_hardened.py` still uses function-scoped real middleware (add comment header)

## 7. Validation

- [ ] 7.1 Run full test suite — all 294 tests pass
- [ ] 7.2 Run `pytest --co` to verify no collection errors with new fixture scoping
- [ ] 7.3 Measure before/after timing (`pytest --durations=0`) and confirm ≥5× speedup
