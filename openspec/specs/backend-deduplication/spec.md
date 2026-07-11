## ADDED Requirements

### Requirement: Single shared datetime format constant
All modules that format SQLite datetime strings SHALL import `SQLITE_DT_FMT` from `app/constants.py`. No module SHALL define its own local copy of this constant.

#### Scenario: Datetime format used in session middleware
- **WHEN** `app/middleware/session.py` needs the SQLite datetime format
- **THEN** it SHALL import `SQLITE_DT_FMT` from `app.constants`

#### Scenario: Datetime format used in auth routes
- **WHEN** `app/routes/auth.py` needs the SQLite datetime format
- **THEN** it SHALL import `SQLITE_DT_FMT` from `app.constants`

### Requirement: Shared product field validators via mixin
The `CreateProductRequest` and `UpdateProductRequest` models SHALL share field validators (`strip_and_reject_blank`, `validate_image_url`) through a common mixin class, not copy-pasted methods.

#### Scenario: Adding a new validator
- **WHEN** a developer adds a new field validator for product models
- **THEN** they SHALL add it in one place (the mixin) and both request models inherit it

#### Scenario: Existing validation behavior preserved
- **WHEN** a product is created with a blank name or invalid image URL
- **THEN** validation SHALL reject it identically to current behavior

### Requirement: Unauthorized response helper in auth routes
The `/v1/auth/me` endpoint SHALL use a shared helper function to construct 401 JSON responses, eliminating duplicated JSONResponse construction.

#### Scenario: Multiple 401 paths in /auth/me
- **WHEN** any of the four authentication checks fail in the `/auth/me` handler
- **THEN** the response SHALL be constructed via a single `_unauthorized(message)` helper

### Requirement: Session user-ID FastAPI dependency
A reusable FastAPI dependency `get_session_user_id` SHALL provide the user_id for the current session, replacing repeated inline `SELECT user_id FROM sessions` queries in route handlers.

#### Scenario: Order route needs user_id
- **WHEN** the `create_order`, `list_my_orders`, or `get_order_detail` route needs the session's user_id
- **THEN** it SHALL receive it via the `get_session_user_id` dependency, not an inline SQL query

### Requirement: Product service field_map helper
The `upsert_product` and `update_product` functions SHALL share a `_build_field_map(data)` helper for constructing the field update dictionary, eliminating duplicated construction logic.

#### Scenario: Adding a new product field
- **WHEN** a developer adds a new product field (e.g., `is_seasonal`)
- **THEN** they SHALL add it in `_build_field_map` once, and both upsert and update use it

### Requirement: Use PaginationParams from common models
All list endpoints SHALL use the `PaginationParams` model or `PageParam`/`LimitParam` type aliases from `app/models/common.py` instead of redefining pagination query params inline.

#### Scenario: Product list endpoint pagination
- **WHEN** the product list endpoint defines its pagination parameters
- **THEN** it SHALL use the shared `PaginationParams` or typed aliases from `app/models/common`

### Requirement: Remove redundant limit clamping
Route handlers SHALL NOT include `limit = min(limit, 100)` when the FastAPI `Query(le=100)` constraint already enforces the maximum.

#### Scenario: Product list with limit=50
- **WHEN** a valid limit is passed via query param
- **THEN** no runtime `min()` call SHALL be applied — the Query constraint is sufficient

### Requirement: Async order route handlers
All order route handlers SHALL be `async def` to match the project convention and avoid unnecessary threadpool dispatch for SQLite I/O.

#### Scenario: create_order handler
- **WHEN** the `create_order` route handler is defined
- **THEN** it SHALL use `async def` consistent with all other route handlers in the project
