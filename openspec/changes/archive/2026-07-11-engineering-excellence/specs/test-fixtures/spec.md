## ADDED Requirements

### Requirement: FakeSessionMiddleware stamps session without DB access
The test infrastructure SHALL provide a `FakeSessionMiddleware` class that sets `request.state.session_id` to a configurable value and `request.state.session_is_new = False` without opening any database connection or parsing cookies.

#### Scenario: Route test uses fake middleware
- **WHEN** a route test fixture creates an app with `FakeSessionMiddleware`
- **THEN** every request to that app has `request.state.session_id` set to the fixture's session ID
- **AND** no `sessions` table query is executed by the middleware

#### Scenario: Fake middleware does not set cookies
- **WHEN** a response is returned through `FakeSessionMiddleware`
- **THEN** no `Set-Cookie` header is added by the middleware layer

### Requirement: Module-scoped app fixture initializes DB once per file
The shared `conftest.py` SHALL provide a module-scoped `app` fixture that calls `init_db()` and `create_app()` exactly once per test module. All tests in that module share the same app instance and database file.

#### Scenario: Two tests in same module share app
- **WHEN** `test_a` and `test_b` both request the `app` fixture in the same file
- **THEN** `init_db()` is called exactly once
- **AND** both tests operate on the same database file

#### Scenario: Different modules get isolated databases
- **WHEN** `test_file_a.py` and `test_file_b.py` both use the module-scoped `app` fixture
- **THEN** each module gets its own `tmp_path` directory and separate database file

### Requirement: Per-test cleanup deletes all rows between tests
The shared `conftest.py` SHALL provide an autouse function-scoped fixture that deletes all rows from data tables after each test completes, in foreign-key-safe order.

#### Scenario: Test data does not leak to next test
- **WHEN** `test_a` inserts a product and completes
- **AND** `test_b` queries products
- **THEN** `test_b` sees zero products (cleanup ran between them)

#### Scenario: Cleanup respects FK order
- **WHEN** cleanup runs after a test that created orders with order_items
- **THEN** `order_items` is deleted before `orders`
- **AND** `cart_items` is deleted before `sessions`
- **AND** no FK constraint violation occurs

### Requirement: make_session helper replaces inline session INSERT
The shared `conftest.py` SHALL provide a `make_session(conn, session_id=None)` helper function that inserts a valid session row and returns the session ID. If no `session_id` is provided, it generates a UUID4.

#### Scenario: Test creates a session with default ID
- **WHEN** a test calls `make_session(conn)`
- **THEN** a row is inserted into `sessions` with a valid UUID4 id, current `created_at`, and `expires_at` 30 days in the future
- **AND** the function returns the generated session ID

#### Scenario: Test creates a session with explicit ID
- **WHEN** a test calls `make_session(conn, session_id="my-test-session")`
- **THEN** a row is inserted with `id = "my-test-session"`

### Requirement: seed_products helper replaces duplicated product insertion
The shared `conftest.py` SHALL provide a `seed_products(conn, products=None)` helper that inserts product rows. If no products list is provided, it inserts a standard set of test products.

#### Scenario: Default product seeding
- **WHEN** a test calls `seed_products(conn)`
- **THEN** a standard set of products is inserted (active, inactive, in-stock, out-of-stock variants)

#### Scenario: Custom product seeding
- **WHEN** a test calls `seed_products(conn, [{"id": "custom", "name": "Custom", "price_cents": 1000, "stock": 5}])`
- **THEN** only that one product is inserted

### Requirement: Consolidated admin_client fixture in conftest
The shared `conftest.py` SHALL provide a module-scoped `admin_client` fixture that returns an `AsyncClient` with admin Bearer auth header set. This replaces the duplicated `admin_app`/`admin_client` pattern in multiple test files.

#### Scenario: Admin client authenticates with API key
- **WHEN** a test uses the `admin_client` fixture
- **THEN** all requests include `Authorization: Bearer <ADMIN_API_KEY>` header
- **AND** the app is configured with a known test admin API key

### Requirement: Service tests use module-scoped connection
Service-layer tests (`test_*_service.py`) SHALL use a module-scoped `sqlite3.Connection` fixture. The connection is created once with `init_db()`, and tests call helper functions to seed data as needed.

#### Scenario: Service test gets raw connection
- **WHEN** `test_cart_service.py` requests the `service_db` fixture
- **THEN** it receives a `sqlite3.Connection` with `row_factory=sqlite3.Row` and `PRAGMA foreign_keys=ON`
- **AND** the schema is already initialized

### Requirement: Session test files remain function-scoped
The files `test_session.py` and `test_session_hardened.py` SHALL continue using function-scoped fixtures with the real `SessionMiddleware`. They MUST NOT use `FakeSessionMiddleware` or module-scoped app fixtures.

#### Scenario: Session tests still test real middleware
- **WHEN** `test_session.py` runs
- **THEN** each test gets a fresh database and real `SessionMiddleware`
- **AND** session creation, validation, expiry, and rotation are tested against actual middleware logic
