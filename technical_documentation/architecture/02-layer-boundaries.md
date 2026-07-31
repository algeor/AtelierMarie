# Layer Boundaries

This project survives by keeping boundaries boring and strict.

## The Two Big Layers

### Layer 1: production e-commerce

Layer 1 is the shop.

It includes:

- products
- taxonomy
- media
- cart
- checkout
- orders
- payments
- shipping
- auth
- admin
- email
- contact
- FAQ/about/legal
- comments/reactions

Layer 1 rules:

- It uses SQLite as system of record.
- It must work without analytics.
- It must work without ML.
- It should degrade around external services when possible.
- It must not trust frontend money totals.

### Layer 2: analytics and ML sandbox

Layer 2 is optional measurement/learning.

It includes:

- consent records
- event ingestion
- JSONL event log
- DuckDB reports
- deferred ML/recommendation ideas

Layer 2 rules:

- Consent first.
- Disabled by default.
- Failure must not break Layer 1.
- No Layer 1 dependency on ML code.

## Internal Backend Boundaries

| Layer | What belongs there | What does not belong there |
|---|---|---|
| Route | HTTP status, Depends, response model, error mapping | Business transactions, provider internals |
| Service | Rules, SQL, transactions, external API orchestration | FastAPI Request/Response objects |
| Model | Pydantic request/response shape | Database access, HTTP calls |
| Config | Env-driven settings | One-off `os.getenv` calls in services |
| Utility | Small reusable helpers | Domain workflows |

## Frontend Boundaries

| Layer | What belongs there |
|---|---|
| `app/[locale]` pages | Route-level composition, metadata, data loading, page state. |
| `components/*` | Reusable display and interaction pieces. |
| `contexts/*` | Shared app state: auth, cart, admin, consent. |
| `lib/api-client.ts` | Real backend calls. |
| `lib/mock-api.ts` | Local dev mock behavior. |
| `lib/types.ts` | Types mirrored from Pydantic models. |
| `messages/*` | User-facing translated strings. |

## Dependency Direction

Good backend direction:

```text
route -> model/dependency/service -> database/util/config
```

Avoid:

```text
service -> route
model -> service
Layer 1 -> ML sandbox
checkout -> analytics success
```

## External Service Boundary

External services stay behind service/client modules.

- Stripe code stays in payment/webhook modules.
- Courier payloads stay in courier clients/services.
- Email provider logic stays in `app/email/providers` and `email_service`.
- Google OAuth logic stays in auth service/routes.

This keeps provider weirdness from leaking into product/order code.

## Boundary Smells

- A route contains a multi-statement checkout transaction.
- A component hardcodes a backend status label that already has a shared map.
- A service imports a React/frontend file.
- A product listing waits for analytics to be available.
- A payment webhook logs raw payloads.
- A model imports a service.
- A frontend page trusts a price computed in the browser.

