# Schema Contracts — Proposal

## Summary

Introduce a formal contract layer that defines the exact shapes of events, analytics table rows, and API responses as Pydantic models — then enforces them at runtime (ingestion, query, response) and at test time (SQL output validation, coverage assertions). The goal is to make schema drift impossible without an explicit, deliberate change.

## Problem

The system has three communication boundaries where data shape is implicit:

1. **Event producer → Consumer:** The frontend SDK sends `{event_type, product_id, metadata}`. The analytics SQL assumes specific fields exist inside `metadata` (e.g., `metadata->>'price'`, `metadata->>'query'`, `metadata->>'result_count'`). Nothing formally connects these. A typo in the SDK or a renamed field silently produces NULLs that propagate as zero-counts in dashboards and broken ML features.

2. **Analytics SQL → Python readers:** The ML recommender and admin dashboard read from `analytics_*` tables. The column names and types exist only in `.sql` files. If a SQL file is refactored (column renamed, type changed), Python consumers break at runtime with a KeyError — or worse, silently get None.

3. **API responses → Frontend:** Pydantic models exist in route handlers but are defined ad-hoc per endpoint. There's no shared vocabulary. A field rename in the response model silently breaks the Next.js frontend with no compile-time or test-time signal.

All three are "stringly-typed" boundaries where **correctness is enforced by human memory alone**.

## Solution

A `app/contracts/` module that is the **single source of truth** for all data shapes crossing system boundaries:

- **Event contracts:** A discriminated union of typed payloads per `event_type`. Validated at ingestion time (already on the hot path via Pydantic). Consumed by analytics SQL tests to assert field availability.

- **Analytics table contracts:** Pydantic models mirroring the output schema of each `analytics_*` table. Consumers import these models. A test suite runs each SQL file and validates the output against the corresponding model.

- **API response contracts:** Shared response models imported by both route handlers and integration tests. The Next.js frontend can auto-generate TypeScript types from the OpenAPI spec (which FastAPI produces from these models).

- **Contract tests:** A test module that asserts structural consistency: every event_type has a payload model, every analytics SQL file has a corresponding row model, every API endpoint response validates against its contract.

## Scope

**In scope:**
- `app/contracts/events.py` — EventType enum + per-type payload models + discriminated union
- `app/contracts/analytics.py` — Row models for all 8 `analytics_*` tables
- `app/contracts/api.py` — Shared response models for public + admin API endpoints
- `app/contracts/__init__.py` — Public re-exports
- `tests/test_contracts.py` — Structural assertions (coverage, SQL↔model sync, enum completeness)
- Event ingestion validates payload against typed model (not just "is it JSON?")
- Analytics readers import row models (type-safe access, not raw dicts)
- API versioning policy documented (additive-only within v1, breaking = v2)

**Out of scope:**
- JSON Schema registry or external schema store
- Event schema versioning with migration (v1 payloads are the baseline — no history needed)
- Code generation from schemas (Pydantic IS the schema)
- Cross-language contracts (no protobuf, no Avro — Python-only system)
- Frontend TypeScript type generation (can be added later via openapi-typescript)
- Runtime schema negotiation or content-type versioning

## Dependencies

**Depends on:**
- `event-ingestion-pipeline` (defines event_type enum and DuckDB schema)
- `analytics-layer` (defines the 8 materialized table schemas)
- `product-catalog` (defines product response shape)
- `admin-dashboard` (defines admin endpoint response shapes)

**Depended on by:**
- All future changes that add event types, analytics tables, or API endpoints (they must update contracts first)
- `frontend-event-sdk` (SDK track() calls must match event payload contracts)
- `storefront-ui` (TypeScript types generated from API contracts)

## Constraints

- Zero runtime overhead on event ingestion hot path (Pydantic validation already happens — this just makes it typed instead of `dict`)
- No new dependencies beyond what's already in the stack (Pydantic, pytest)
- Contract models are plain Pydantic — no metaprogramming, no code generation, no magic
- Must not slow down development — adding a new event type is: add enum value + add payload model + done
