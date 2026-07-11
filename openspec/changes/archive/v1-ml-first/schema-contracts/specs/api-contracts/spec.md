## ADDED Requirements

### Requirement: Shared response models for all public API endpoints
The system SHALL define response Pydantic models in `app/contracts/api.py` that are used as the `response_model` parameter in FastAPI route decorators. These models are the single source of truth for what the API returns.

#### Scenario: Product list endpoint uses ProductListItem
- **WHEN** GET /v1/products returns a list of products
- **THEN** each item in the response validates against `ProductListItem(id: str, name: str, price: Decimal, category: str | None, image_url: str | None, stock_quantity: int, in_stock: bool, is_featured: bool)`

#### Scenario: Product detail endpoint uses ProductDetail
- **WHEN** GET /v1/products/{id} returns a product
- **THEN** the response validates against `ProductDetail` (extends ProductListItem with description and created_at)

#### Scenario: Paginated responses use standard wrapper
- **WHEN** any list endpoint returns paginated results
- **THEN** the response validates against `PaginatedResponse[ItemModel](items: list[ItemModel], total: int, page: int, per_page: int)`

#### Scenario: Admin product endpoint uses AdminProductItem
- **WHEN** GET /v1/admin/products returns products with metrics
- **THEN** each item validates against `AdminProductItem` (extends ProductListItem with is_active, total_views, total_cart_adds, total_orders)

#### Scenario: Dashboard endpoint uses DashboardMetrics
- **WHEN** GET /v1/admin/dashboard returns metrics
- **THEN** the response validates against `DashboardMetrics` containing all KPI fields plus freshness metadata

---

### Requirement: Response models forbid extra fields
The system SHALL configure all API response models with `model_config = ConfigDict(extra="forbid")`. This prevents accidental data leakage where a database query returns fields not intended for the API consumer.

#### Scenario: Extra field in route handler raises error
- **WHEN** a route handler returns a dict with a field not in the response model
- **THEN** FastAPI raises a validation error (caught in development/testing)
- **AND** the field does not leak to the client

#### Scenario: Database column not in model is stripped
- **WHEN** a SQLite query returns `is_active` but the public `ProductListItem` model does not include it
- **THEN** the field is not present in the API response (model filters it out)

#### Scenario: Test asserts all models use extra=forbid
- **WHEN** `test_api_responses_are_strict` runs
- **THEN** it iterates all response models in `app/contracts/api.py`
- **AND** asserts each has `extra="forbid"` in model_config

---

### Requirement: API versioning policy enforced via contract diff
The system SHALL follow an additive-only policy within `/v1/`: new optional fields may be added, but no fields may be removed, renamed, or have their type changed. Breaking changes require a new API version (`/v2/`).

#### Scenario: Adding an optional field is non-breaking
- **WHEN** `ProductListItem` gains `rating: Decimal | None = None`
- **THEN** existing clients that don't read `rating` continue working
- **AND** no version bump is required

#### Scenario: Removing a field is breaking
- **WHEN** a developer removes `is_featured` from `ProductListItem`
- **THEN** existing clients that read `is_featured` would break
- **AND** this change requires either: keep the field, or introduce `/v2/products`

#### Scenario: Renaming a field is breaking
- **WHEN** a developer renames `stock_quantity` to `stock` in `ProductListItem`
- **THEN** existing clients that read `stock_quantity` would break
- **AND** the correct approach is: add `stock` as alias, deprecate `stock_quantity`, remove in v2

#### Scenario: Making an optional request parameter required is breaking
- **WHEN** `category` filter on GET /v1/products becomes required
- **THEN** existing clients that call without `category` would get 422
- **AND** this requires a new endpoint or version

---

### Requirement: OpenAPI schema generated from contract models
The system SHALL rely on FastAPI's automatic OpenAPI generation from the Pydantic response models. The OpenAPI spec at `/docs` and `/openapi.json` always reflects the current contracts.

#### Scenario: OpenAPI spec matches response models
- **WHEN** a developer visits `/openapi.json`
- **THEN** the schema definitions match the Pydantic models in `app/contracts/api.py` exactly
- **AND** field types, optionality, and descriptions are preserved

#### Scenario: Frontend can generate types from OpenAPI
- **WHEN** a frontend developer runs a TypeScript codegen tool against `/openapi.json`
- **THEN** the generated types match the API response shapes exactly
- **AND** any contract change is reflected in the next codegen run

---

### Requirement: Integration test validates live endpoint against contract
The system SHALL include integration tests that call each API endpoint and validate the response against the corresponding contract model (using Pydantic's strict validation).

#### Scenario: Product list response matches contract
- **WHEN** integration test calls GET /v1/products
- **THEN** it parses the JSON response through `PaginatedProducts.model_validate(response.json())`
- **AND** the test passes (all fields present, correct types)

#### Scenario: Dashboard response matches contract
- **WHEN** integration test calls GET /v1/admin/dashboard (with auth)
- **THEN** it parses the JSON response through `DashboardMetrics.model_validate(response.json())`
- **AND** the test passes

#### Scenario: Response with unexpected field fails strict validation
- **WHEN** a route handler accidentally includes an internal field (e.g., `_internal_score`)
- **THEN** the integration test fails because `extra="forbid"` rejects unknown fields

---

### Requirement: Error response contract
The system SHALL define a standard error response model used across all endpoints for 4xx and 5xx responses.

#### Scenario: Validation error (422) follows standard shape
- **WHEN** any endpoint returns HTTP 422
- **THEN** the response body matches `ErrorResponse(detail: list[ErrorDetail])` where each `ErrorDetail` has `loc` (field path), `msg` (human-readable), and `type` (error code)

#### Scenario: Not found (404) follows standard shape
- **WHEN** any endpoint returns HTTP 404
- **THEN** the response body matches `ErrorResponse(detail: str)` with a human-readable message

#### Scenario: Auth error (401/403) follows standard shape
- **WHEN** any endpoint returns HTTP 401 or 403
- **THEN** the response body matches `ErrorResponse(detail: str)` indicating the auth failure reason
