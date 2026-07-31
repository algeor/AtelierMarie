# Analytics Production Readiness

This note tracks what must be true before first-party analytics is enabled in
production. It is not legal advice; it is the engineering/legal handoff checklist
for the `first-party-funnel-analytics` change.

## Current implementation state

- Analytics is first-party only: storefront events go to the Atelier Marie API,
  not to a third-party analytics provider.
- Analytics remains disabled unless `ANALYTICS_ENABLED=true`.
- Production startup rejects analytics unless `ANALYTICS_LEGAL_APPROVED=true`.
- The cookie popup supports analytics acceptance and necessary-only rejection.
- Public event ingestion requires a current server-side consent record for the
  session before events are persisted.
- Analytics retention cleanup is wired into the runtime cleanup loop.
- GDPR erasure can pseudonymize analytics records by session, user, or order.

## Must change before production enablement

- Replace the remaining legal identity placeholders in the English and Bulgarian
  legal copy: legal name, geographic address, registration/VAT status, and
  responsible-party details.
- Get owner/legal approval for the English and Bulgarian Privacy Policy and
  Cookie Policy wording.
- Confirm the production retention period is acceptable; current analytics
  retention is configured as 395 days.
- Confirm the production deployment has durable private storage for:
  - `ANALYTICS_DATA_DIR`
  - `ANALYTICS_EVENTS_JSONL_PATH`
  - `ANALYTICS_DUCKDB_PATH`
- Confirm backups include analytics storage only if the owner wants reports to
  survive host rebuilds.
- Confirm admin users can access `/admin/analytics` and review delivery health.
- Only then set production:
  - `ANALYTICS_ENABLED=true`
  - `ANALYTICS_LEGAL_APPROVED=true`

## Commit hygiene before hooks

- Do not commit SQLite sidecars such as `atelier_marie.db-shm` or
  `atelier_marie.db-wal`.
- Do not commit local analytics files such as `analytics-data/`, `*.duckdb`, or
  `*.jsonl`.
- Keep `.env` files out of git; use `.env.example` only for documented defaults.

## Verification already run

- `uv run pytest tests/test_lifespan.py tests/test_analytics.py tests/test_config.py -q`
- `uv run ruff check app tests/test_analytics.py tests/test_config.py`
- `npm run test -- __tests__/lib/analytics.test.ts __tests__/contexts/CookieConsentContext.test.tsx __tests__/components/analytics-copy.test.ts __tests__/components/analytics-instrumentation.test.tsx`
- `npm run build`
- `openspec validate first-party-funnel-analytics --strict`
