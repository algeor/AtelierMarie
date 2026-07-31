# Analytics And ML Boundary

Use this when touching tracking, cookie consent, analytics ingestion, admin analytics, or old ML/recommendation specs.

## The Rule

Analytics can be useful. It is not allowed to become required for sales.

Checkout, products, cart, auth, shipping, payments, and email must work when analytics is disabled.

## Main Backend Files

- `app/routes/analytics.py`: public consent and event ingestion endpoints.
- `app/routes/admin.py`: admin analytics report endpoints.
- `app/services/analytics_service.py`: consent, event validation/storage, DuckDB load/reporting, cleanup.
- `app/models/analytics.py`: event and report models.
- `app/config.py`: analytics settings.

## Main Frontend Files

- `frontend/contexts/CookieConsentContext.tsx`
- `frontend/lib/analytics.ts`
- `frontend/lib/tracking.ts`
- `frontend/components/layout/CookieSettingsButton.tsx`
- `frontend/app/[locale]/admin/analytics/page.tsx`
- `frontend/messages/en.json`, `frontend/messages/bg.json`

## Storage Model

- Consent is stored in SQLite by session.
- Events can be appended to JSONL.
- DuckDB is used for analytics reporting/aggregation.
- Backend order totals can be compared against analytics events for coverage.

## Consent Rules

- Analytics is off by default.
- Production analytics requires legal approval config.
- Frontend emits only after consent.
- Consent version changes can resurface the banner.
- Users can change consent later.
- Checkout snapshots analytics consent on the order.

## Event Rules

- Event ingestion validates event type/properties.
- Event IDs support idempotency.
- Event payload size is limited.
- Invalid events are rejected/recorded without breaking storefront flows.
- Purchase confirmation can be recorded from backend order creation for better coverage.

## Admin Analytics

Admin analytics covers:

- summary metrics
- funnel report
- product metrics
- checkout/delivery/payment metrics
- health
- CSV export

Reports must tolerate missing DuckDB/empty event data.

## ML Boundary

The archive contains old ML-first specs for recommendations, event pipelines, analytics layers, and deployment. Treat them as context only unless a new change explicitly revives them.

Current rule:

- No Layer 1 import from ML sandbox.
- No checkout dependency on recommendations.
- No product listing dependency on recommendation jobs.
- If recommendations return later, they must have a fallback like popular/products and be safe to disable.

## Safe Change Checklist

- Analytics disabled path tested.
- Consent denial path tested.
- Tracking failure does not block UI.
- No Layer 1 module imports sandbox-only code.
- Admin analytics handles empty/missing data.
- Privacy/cookie copy stays accurate.

