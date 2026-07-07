## Why

The project skeleton provides a running FastAPI app with database and session management, but no API contracts exist yet. Without Pydantic request/response models and TypeScript types defined upfront, backend and frontend development cannot proceed in parallel. This change establishes the full API contract layer so backend implementation (routes, services) and frontend UI development can happen independently against the same agreed shapes.

## What Changes

- **New `app/models/` package** with Pydantic schemas for all domain entities: products, cart, orders, users, auth, and shared error responses
- **Request models** (CreateProduct, UpdateProduct, AddToCart, CreateOrder, etc.) alongside response models — full input/output contract
- **Standardized error response** shape used across all endpoints
- **New `frontend/` Next.js project** scaffolded with TypeScript types mirroring the Pydantic models
- **`frontend/lib/mock-api.ts`** providing hardcoded mock responses matching the API contract, enabling frontend development without a running backend
- **Extended `app/config.py`** with any additional config vars needed for new capabilities (image upload path, CORS origins)
- **Router registration pattern** added to `app/main.py` (empty routers wired up, ready for implementation)

## Capabilities

### New Capabilities
- `api-models`: All Pydantic request/response schemas covering products, cart, orders, users, auth, and errors — the single source of truth for API shape
- `frontend-scaffold`: Next.js 14 project setup with TypeScript types derived from API models and a mock API layer for parallel frontend development

### Modified Capabilities
- `project-foundation`: Extended config (CORS origins, static file path), router registration pattern in app factory, models package added to application structure

## Impact

- **Code:** New `app/models/` package (~6 files), new `frontend/` directory (Next.js scaffold + types + mock API), minor updates to `app/main.py` and `app/config.py`
- **APIs:** No functional endpoints yet — only the contract shapes. Routers are registered but return 501 until implementation phases fill them in
- **Dependencies:** `pyproject.toml` gains no new production deps (Pydantic already included). Frontend gets its own `package.json` with Next.js 14 deps
- **Systems:** Frontend developers can run `npm run dev` against mocks immediately after this change
