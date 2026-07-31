# Errors, Validation, And Logging

This project uses a standard error envelope and structured logs.

## Standard Error Shape

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": null
  }
}
```

Why it matters:

- frontend can localize/map error codes
- tests can assert stable codes
- API consumers get predictable failures

## Global Exception Handlers

Registered in `app/exceptions.py` through `register_exception_handlers(app)`.

They cover:

- Pydantic/FastAPI validation errors
- Starlette/FastAPI HTTP exceptions
- cart service errors
- order service errors
- video upload/transcode errors

Routes still map many domain errors directly when the response needs custom details.

## Validation Layers

Validation happens in more than one place.

| Layer | Examples |
|---|---|
| Pydantic model | field type, min/max length, `Literal` status values. |
| Route | content type, method availability from settings. |
| Service | stock, state transition, delivery method enabled, office exists. |
| Database | constraints like `stock >= 0`, positive cents, unique keys. |

Do not rely on only one layer for critical invariants.

## Custom Service Errors

Use custom exceptions for expected domain failures.

Examples:

- empty cart
- insufficient stock
- invalid delivery office
- invalid order state transition
- payment already paid
- wrong payment method
- video too long

Benefits:

- service tests can assert exact failure
- route can map to correct HTTP code
- frontend gets stable error code

## Logging Rules

Use:

```python
import structlog
logger = structlog.get_logger(__name__)
```

Log useful IDs:

- `request_id`
- `order_id`
- `product_id`
- `campaign_id`
- `event_id`

Do not log PII:

- raw email
- phone
- address
- customer notes
- raw webhook payload

## Request IDs

`RequestIdMiddleware` assigns/propagates request IDs.

Use them in logs for multi-step admin actions and provider calls when available.

## 422 Errors

Pydantic validation errors are sanitized before returning.

That means bytes and unusual objects are converted to JSON-safe values.

## Error Handling Checklist

- Is the error expected? Make a custom exception.
- Does the route map it to a useful HTTP code?
- Does response use the standard envelope?
- Are details safe and non-PII?
- Is the original exception chained if wrapped?
- Is there a test for the failure path?

