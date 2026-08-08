# First Party Funnel Analytics Manual Launch Plan

OpenSpec change: `first-party-funnel-analytics`.
Manual production gates moved from the change tasks before archive.

## Preconditions

- Analytics code, consent UI, policy copy, and admin monitoring are deployed to staging or development.
- Analytics collection remains disabled in production until approval is recorded.
- A seeded dataset exists for dashboard comparison.
- Owner/legal review has access to the final privacy and cookie copy in both locales.

## Consent And Collection Smoke

1. Reject analytics consent.
   - Expected: no behavioral analytics requests are sent.
   - Expected: queued analytics events are cleared.

2. Accept analytics consent.
   - Expected: allowed storefront events are delivered to the backend.
   - Expected: payloads exclude email, phone, name, address, notes, raw IP, and payment details.

3. Withdraw consent.
   - Expected: future events stop.
   - Expected: queued events are cleared.

4. Complete a checkout with analytics accepted.
   - Expected: order-created business truth exists in transactional tables.
   - Expected: consented purchase analytics appears only for consented sessions.

## Admin Monitoring Smoke

1. Open the admin analytics dashboard.
   - Expected: funnel, product, checkout, delivery, and purchase metrics render.
   - Expected: counts clearly separate consented analytics from all-order business totals.

2. Compare dashboard order coverage to backend order counts for the same date range.
   - Expected: consented-order coverage is labeled as coverage, not total sales.

3. Rebuild DuckDB from JSONL in staging/dev.
   - Expected: rebuilt counts match JSONL source counts.

## Owner/Legal Approval Gate

1. Review English privacy and cookie copy.
   - Record approval or requested edits.

2. Review Bulgarian privacy and cookie copy.
   - Record approval or requested edits.

3. Confirm the consent UI wording is acceptable.
   - Record approval or requested edits.

4. Confirm production enablement date and responsible approver.
   - Analytics may be enabled in production only after this approval exists.

## Production Enablement Checklist

1. Confirm consent UI is live.
2. Confirm privacy/cookie policy copy is live.
3. Confirm admin monitoring is accessible to the owner/admin.
4. Enable analytics collection through config.
5. Place one consented test order or staging-equivalent production-safe flow.
6. Confirm event delivery health and dashboard coverage after enablement.

## Evidence To Record

- Browser, environment, and commit tested.
- Owner/legal approver and approval date.
- Screenshots of consent UI, privacy/cookie copy, and admin analytics dashboard.
- Event delivery health before and after production enablement.
