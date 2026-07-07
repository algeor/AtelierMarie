## ADDED Requirements

### Requirement: All error responses use standard ErrorResponse envelope
The system SHALL return all error responses (4xx, 5xx) in the format:
```json
{
  "error": {
    "code": "MACHINE_READABLE_CODE",
    "message": "Human-readable description",
    "details": null | { ... }
  }
}
```
The `code` field MUST be an UPPER_SNAKE_CASE string. The `message` field MUST be a non-empty string. The `details` field MAY be null or an object with additional context.

#### Scenario: Validation error uses standard envelope
- **WHEN** a request fails Pydantic validation (e.g., missing required field)
- **THEN** the system returns 422 with body `{error: {code: "VALIDATION_ERROR", message: "Request validation failed", details: {fields: [{field: "name", message: "Field required"}]}}}` where `details.fields` lists each invalid field

#### Scenario: Not found error uses standard envelope
- **WHEN** a requested resource does not exist (e.g., `GET /v1/products/nonexistent`)
- **THEN** the system returns 404 with body `{error: {code: "NOT_FOUND", message: "Product not found", details: null}}`

#### Scenario: Conflict error uses standard envelope
- **WHEN** a business rule violation occurs (e.g., adding out-of-stock item to cart)
- **THEN** the system returns 409 with body `{error: {code: "INSUFFICIENT_STOCK", message: "...", details: {product_id: "...", requested: 5, available: 2}}}`

Note: The `available` field is intentionally exposed to all callers. The frontend displays stock counts on product pages anyway, so this does not leak information that isn't already public. This is a deliberate UX trade-off — clear error messages enable the frontend to suggest "only 2 remaining" without an additional API call.

### Requirement: Custom exception handler for RequestValidationError
The system SHALL override FastAPI's default 422 response to use the `ErrorResponse` envelope. The `details.fields` array MUST include `field` (dot-notation path, e.g., `body.price_cents`) and `message` (human-readable) for each validation failure.

#### Scenario: Multiple validation errors reported
- **WHEN** a request has multiple invalid fields (e.g., `price_cents: -1` and `name: ""`)
- **THEN** the 422 response `details.fields` array contains one entry per invalid field with its path and message

#### Scenario: Nested field path reported correctly
- **WHEN** validation fails on a nested field (e.g., `items[0].quantity`)
- **THEN** the `field` value uses dot-and-bracket notation: `body.items[0].quantity`

### Requirement: Custom exception handler for HTTPException
The system SHALL convert FastAPI's `HTTPException` into the `ErrorResponse` envelope. The handling rule:
- If `HTTPException.detail` is a **dict** containing `code` and `message` keys: extract them into the `ErrorResponse` envelope, placing all remaining keys into `details`.
- If `HTTPException.detail` is a **string**: use a status-code-derived code (e.g., 403 → `"FORBIDDEN"`, 401 → `"UNAUTHORIZED"`) and the string as `message`, with `details: null`.

#### Scenario: HTTPException with string detail
- **WHEN** a route raises `HTTPException(status_code=403, detail="Admin access required")`
- **THEN** the response is `{error: {code: "FORBIDDEN", message: "Admin access required", details: null}}`

#### Scenario: HTTPException with dict detail containing code and message
- **WHEN** a route raises `HTTPException(status_code=409, detail={"code": "CART_FULL", "message": "Cart is full", "max_items": 20})`
- **THEN** the response is `{error: {code: "CART_FULL", message: "Cart is full", details: {max_items: 20}}}`

### Requirement: Service exceptions mapped to HTTP status codes
The system SHALL define a base exception class `ServiceError(Exception)` with attributes: `status_code: int`, `error_code: str`, `message: str`, `details: dict | None`. All service exceptions inherit from it. A single exception handler catches `ServiceError` and formats the response from its attributes.

Concrete exception classes and their defaults:
- `ProductNotFoundError` → 404, code `"NOT_FOUND"`
- `InsufficientStockError` → 409, code `"INSUFFICIENT_STOCK"`
- `InvalidStateTransitionError` → 422, code `"INVALID_STATE_TRANSITION"` (422 chosen over 409 to align with core-ecommerce design decision)
- `CartFullError` → 409, code `"CART_FULL"`
- `QuantityLimitError` → 422, code `"QUANTITY_LIMIT_EXCEEDED"`
- `OrderNotFoundError` → 404, code `"NOT_FOUND"`
- `AuthenticationError` → 401, code `"UNAUTHORIZED"`

Note: HTTP 422 is shared by `RequestValidationError` (code `"VALIDATION_ERROR"`), `InvalidStateTransitionError` (code `"INVALID_STATE_TRANSITION"`), and `QuantityLimitError` (code `"QUANTITY_LIMIT_EXCEEDED"`). Frontend clients MUST discriminate 422 responses by inspecting `error.code`, not HTTP status alone. The `code` field provides the machine-readable distinction between "malformed request" and "well-formed but business-rule-rejected."

#### Scenario: Service exception carries details
- **WHEN** `InsufficientStockError` is raised with `product_id="lavender-dream"`, `requested=5`, `available=2`
- **THEN** the 409 response includes `details: {product_id: "lavender-dream", requested: 5, available: 2}`

#### Scenario: Unhandled exception returns 500 with safe message
- **WHEN** an unexpected exception occurs in a route handler
- **THEN** the system returns 500 with `{error: {code: "INTERNAL_ERROR", message: "An unexpected error occurred", details: null}}` and MUST NOT leak stack traces or internal details in the response body
