# Analytics And Consent

Analytics is optional and consent-gated.

## Main Backend Files

- `app/models/analytics.py`
- `app/routes/analytics.py`
- `app/routes/admin.py` analytics endpoints
- `app/services/analytics_service.py`
- `app/config.py`

## Main Frontend Files

- `frontend/contexts/CookieConsentContext.tsx`
- `frontend/lib/analytics.ts`
- `frontend/lib/tracking.ts`
- `frontend/app/[locale]/admin/analytics/page.tsx`
- `frontend/components/layout/CookieSettingsButton.tsx`

## Event Flow

```text
user grants analytics consent
  -> frontend records consent preference
  -> backend stores analytics_consents row for session/version
  -> tracking helpers emit allowed event types
  -> /v1/analytics/events validates batch
  -> event written to JSONL and DuckDB
  -> admin reports query DuckDB and Postgres order totals
```

## Consent Rules

- Analytics disabled means ingestion returns disabled result.
- Session is required.
- Consent version must match current settings.
- No frontend event emission without consent.
- Backend purchase event also checks analytics consent.

## Event Validation

Validation rejects:

- unknown properties for event type
- PII-like property keys
- PII-like values containing email/newlines
- oversized property payloads
- too many properties
- unsupported value types
- batches larger than configured limit

## Storage

Storage pieces:

- Postgres `analytics_consents` for consent state.
- JSONL file for durable event log.
- DuckDB `analytics_events` for reports.
- DuckDB health/state tables for delivery status.

JSONL remains useful as rebuild source for DuckDB.

## Admin Reports

Reports include:

- funnel steps
- summary
- product metrics
- checkout/delivery/payment metrics
- health
- CSV export

Reports should handle empty data without crashing.

## Layer Boundary

Analytics must not decide whether checkout succeeds.

`record_purchase_confirmed(...)` catches and logs its own failures.

## Safe Change Checklist

- Analytics disabled path tested.
- Consent denied path tested.
- PII reject rules still work.
- Admin reports handle empty/missing data.
- Layer 1 code does not require DuckDB.
- Privacy/cookie copy matches actual tracking behavior.

