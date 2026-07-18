## ADDED Requirements

### Requirement: All endpoints have summary and description
Every route decorator in the application MUST include `summary` (short title, ≤60 chars) and `description` (1-3 sentence explanation) kwargs. These appear in the auto-generated OpenAPI spec (Swagger/ReDoc).

#### Scenario: Product list endpoint documented
- **WHEN** a developer opens `/docs` (Swagger UI)
- **THEN** the `GET /v1/products` endpoint shows a summary (e.g., "List products") and a description explaining filters, pagination, and search

#### Scenario: Admin endpoint documented
- **WHEN** a developer opens `/docs`
- **THEN** admin endpoints show their auth requirements in the description (e.g., "Requires admin JWT or API key")

### Requirement: Endpoints grouped by tags
The system SHALL assign tags to all routes for logical grouping in API docs:
- `Products` — public product browsing
- `Cart` — cart operations
- `Orders` — order placement and viewing
- `Auth` — authentication flow
- `Admin` — admin-only operations

#### Scenario: Tag grouping in Swagger UI
- **WHEN** a developer opens `/docs`
- **THEN** endpoints are grouped under their respective tags with the tag name as the section header

### Requirement: Error responses documented in OpenAPI spec
All endpoints MUST declare their possible error responses using the `responses` kwarg on the route decorator. At minimum: 422 (validation), 404 (not found where applicable), 401/403 (auth-protected endpoints).

#### Scenario: Product detail shows 404 response
- **WHEN** a developer views `GET /v1/products/{product_id}` in Swagger UI
- **THEN** the "Responses" section shows both 200 (success) and 404 (not found) with the ErrorResponse schema

#### Scenario: Cart add shows 409 response
- **WHEN** a developer views `POST /v1/cart` in Swagger UI
- **THEN** the "Responses" section includes 409 (Conflict — insufficient stock or cart full)

### Requirement: FastAPI app metadata configured
The `FastAPI()` app instance MUST be configured with:
- `title`: "Atelier Marie API"
- `version`: "1.0.0"
- `description`: Brief description of the API purpose
- `docs_url`: "/docs" (Swagger UI, default)
- `redoc_url`: "/redoc" (ReDoc, default)

#### Scenario: API title shown in docs
- **WHEN** a developer opens `/docs`
- **THEN** the page title shows "Atelier Marie API" and version "1.0.0"

### Requirement: Response models specified on all success responses
Every route MUST specify `response_model` in its decorator for the success case. This ensures the OpenAPI spec accurately describes response shapes and Pydantic serialization is applied.

#### Scenario: Product list has response model
- **WHEN** `GET /v1/products` is called
- **THEN** the response is serialized through `ProductListResponse` (excluding unset optional fields, applying aliases if any)

#### Scenario: Undocumented fields not leaked
- **WHEN** internal data (e.g., a debug field added during development) is accidentally included in a response dict
- **THEN** the `response_model` filters it out — only declared fields are returned to the client

### Requirement: Pagination documented consistently
All list endpoints MUST document their pagination query parameters (`page`, `limit`) in the OpenAPI spec with descriptions, defaults, and constraints (min/max).

#### Scenario: Pagination params visible in docs
- **WHEN** a developer views any list endpoint in Swagger UI
- **THEN** the Parameters section shows `page` (default 1, min 1) and `limit` (default 20, min 1, max 100) with descriptions
