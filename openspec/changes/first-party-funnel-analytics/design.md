## Context

The storefront currently states that it has no analytics, advertising pixels, profiling, or non-essential tracking. That avoids consent complexity, but it also means the business cannot evaluate discovery, product consideration, cart, checkout, delivery, payment, or retention behavior.

The app already has an anonymous session cookie for cart and checkout continuity, a FastAPI backend, a Next.js frontend, existing admin authentication, and an older archived plan that selected first-party DuckDB analytics over hosted tracking tools. That is the strongest local precedent, but the new design must add explicit consent controls and legal copy before non-essential behavioral measurement is enabled.

## Goals / Non-Goals

**Goals:**
- Measure the core commerce funnel with a minimal first-party event taxonomy.
- Gate non-essential behavioral analytics behind clear consent.
- Keep analytics data on the Atelier Marie backend instead of sending it to third-party pixels by default.
- Provide admin-visible funnel, product, checkout, delivery, payment, and purchase metrics.
- Keep consented behavioral funnel metrics distinct from all-order business totals.
- Validate event coverage, event delivery health, and consented-order coverage against backend order records.
- Keep analytics failures non-blocking for browsing, cart, checkout, payment, and admin operations.

**Non-Goals:**
- No Google Analytics, Meta Pixel, TikTok Pixel, advertising audiences, session replay, heatmaps, device fingerprinting, or cross-site tracking.
- No personalization, recommendation engine, or ML work in this change.
- No tracking of emails, phone numbers, delivery addresses, customer names, free-form notes, or raw payment details in analytics events.
- No attempt to backfill historic behavior that was never measured.

## Decisions

### 1. Use first-party analytics as the golden standard

Use a small in-repo analytics layer instead of adding a hosted analytics SDK. The frontend emits events to the Atelier Marie API; the backend validates and stores them.

Alternatives considered:
- Google Analytics: mature, but adds consent and third-party tracking complexity.
- PostHog/Plausible/Matomo Cloud: useful products, but still introduces a provider and data-processing review before the business has a stable taxonomy.
- Server logs only: too coarse for product, cart, checkout, and delivery-step behavior.

### 2. Use native browser delivery, not a frontend analytics library

Create `frontend/lib/analytics.ts` with typed event helpers, an in-memory queue, `navigator.sendBeacon()` for unload-safe delivery, and `fetch(..., { keepalive: true })` fallback.

Rationale:
- No frontend dependency required.
- Works with the current Next.js stack.
- Keeps the event contract explicit and testable.

### 3. Store durable events as JSONL, query through DuckDB

Write accepted events to append-only JSONL first, then load them into a DuckDB database for admin reporting. JSONL is the durable event log; DuckDB is the query/index layer and can be rebuilt from JSONL.

Rationale:
- JSONL append is simple and robust for low boutique traffic.
- DuckDB gives fast aggregate queries without competing with SQLite order/cart transactions.
- Rebuildability makes schema iteration safer.

Alternatives considered:
- SQLite analytics tables: simpler dependency set, but long aggregate scans would compete with transactional data.
- PostgreSQL/ClickHouse: stronger at scale, but overkill for the current infrastructure target.

### 4. Treat consent as the gate for behavioral events

Necessary cookies keep powering cart, checkout, auth, locale, and security. Behavioral analytics events are stored only after the user grants analytics consent. If analytics consent is absent or rejected, the frontend does not send behavioral events and clears queued analytics events.

The consent state is stored in a first-party preference cookie such as `atelier_cookie_consent` with consent version, analytics boolean, locale, and timestamp. The existing session cookie is disclosed as necessary for cart/checkout, and also disclosed as the pseudonymous join key for analytics only when analytics is accepted.

### 5. Keep event identity pseudonymous and server-derived

The event endpoint derives `session_id` from the existing backend session middleware and optional `user_id` from authenticated state. The client does not submit arbitrary session IDs. Event payloads are validated against an allowlist and must not include PII.

Allowed event context includes product IDs, category/filter names, price/value cents, currency, delivery method/courier, payment method/redirect provider, page path, locale, and bounded metadata. Disallowed context includes email, phone, name, address, note text, raw user agent, raw IP, and payment card data.

### 6. Use server confirmation for final purchase metrics

Frontend events cover consideration and intent. Final `purchase_confirmed` is recorded when the backend successfully creates an order, for every payment method. This treats purchase as the completed order creation moment, not final cash/card settlement.

`order_submit` remains the user's submit attempt. `purchase_confirmed` is the successful order creation outcome. `payment_redirect` remains a separate card-payment handoff event.

### 7. Design admin analytics around decisions, not raw exhaust

The admin panel should show the metrics the owner can act on:
- Funnel conversion by step.
- Event delivery success rate.
- Product views, add-to-cart count, purchase count, revenue, and conversion.
- Listing filter usage.
- Cart opens and add-to-cart rate.
- Checkout start, delivery selected, quote selected, order submitted, payment redirect, and purchase confirmation rates.
- Dashboard coverage against backend order count/revenue for the same date range.

Raw event browsing can exist for debugging, but it must be admin-only, paginated, filtered, and avoid PII.

### 8. Snapshot consent onto orders for coverage and reliable purchase events

Store an analytics consent snapshot on the order, or an equivalent analytics consent ledger keyed by order/session, at checkout time.

This lets the backend reliably record `purchase_confirmed` at order creation only when analytics consent exists, and lets the admin dashboard distinguish all backend orders from the subset that was eligible for analytics measurement.

### 9. Separate behavioral analytics, business truth, and coverage

The admin dashboard must not present consented analytics as total traffic. Use three metric families:
- Consented behavioral funnel: product/cart/checkout behavior from sessions that accepted analytics.
- Business truth: all backend orders and revenue from transactional tables.
- Coverage: how many backend orders are represented by consented analytics events, with deltas clearly labeled as coverage gaps rather than data errors.

This avoids a logical mismatch where consented `purchase_confirmed` events are compared directly against all backend orders.

## Risks / Trade-offs

- [Consent reduces sample size] -> Show consented-session counts and avoid treating analytics as total traffic.
- [Duplicate events from retries/back/refresh] -> Require client-generated `event_id`, idempotent ingestion, and backend de-duplication.
- [Analytics failures affect checkout] -> Make emission fire-and-forget; never block cart, checkout, or payment paths on analytics writes.
- [JSONL/DuckDB drift] -> Treat JSONL as source of truth and add a rebuild command plus count-consistency tests.
- [Policy mismatch] -> Update cookie/privacy copy before enabling the event endpoint in production.
- [PII leakage through metadata] -> Validate payload keys and value lengths; reject unknown keys for sensitive events.
- [Low volume makes percentages noisy] -> Include absolute counts beside rates in the admin dashboard.
- [Order coverage is lower than total orders] -> Snapshot analytics consent at checkout and show consented-order coverage beside all-order totals.
- [Analytics erasure omitted] -> Add analytics data to the GDPR erasure/retention model before production enablement.
- [Shipping quote event lands before shipping pricing] -> Define `shipping_quote_selected` as dormant until the `shipping-pricing` flow exposes selectable quotes.

## Migration Plan

1. Add configuration with analytics disabled by default in production until policy copy and consent UI ship.
2. Add backend event models, ingestion endpoint, JSONL writer, DuckDB schema, and admin query service behind feature flags.
3. Add frontend consent popup and cookie/settings controls.
4. Update privacy and cookie policy text in English and Bulgarian.
5. Add a checkout-time analytics consent snapshot for order-created purchase confirmation and coverage reporting.
6. Add frontend analytics wrapper and instrument product, listing, cart, checkout, delivery, payment, and confirmation events.
7. Add admin analytics API and `/admin/analytics` page.
8. Add tests for consent gating, event coverage, ingestion validation, admin access, delivery health, and consented-order coverage.
9. Enable analytics in staging/dev, inspect event logs and dashboard coverage, then enable in production only after legal copy is reviewed.

Rollback:
- Disable analytics collection through config.
- Keep consent UI available so users can update preferences.
- Leave previously collected first-party analytics available to admins until retention rules delete or export them.

## Open Questions

- Confirm final retention period for analytics JSONL/DuckDB data before launch.
- Confirm whether analytics export is needed in the first implementation or can remain a later admin enhancement.
- Confirm the exact legal wording with the business owner before enabling production tracking.
- Confirm whether shipping quote analytics should wait for `shipping-pricing` or be implemented as a no-op event until quotes exist.
