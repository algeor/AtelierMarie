## Why

Atelier Marie cannot currently measure product discovery, product consideration, cart behavior, checkout progress, delivery selection, payment handoff, or purchase confirmation. That keeps the current app simple from a consent perspective, but it makes commercial decisions about navigation, hero content, pricing, delivery, checkout, and product pages guesswork.

This change introduces a minimal, privacy-conscious first-party funnel measurement layer before serious conversion optimization work begins.

## What Changes

- Add a first-party analytics event contract for storefront funnel events: `product_view`, `listing_filter`, `add_to_cart`, `cart_open`, `checkout_start`, `delivery_selected`, `shipping_quote_selected`, `order_submit`, `payment_redirect`, and `purchase_confirmed`.
- Add a consent-aware frontend analytics wrapper that queues and sends eligible events via `sendBeacon`/`fetch` without third-party pixels.
- Add a public analytics ingestion API for validated single-event and batched event delivery.
- Store analytics events in an append-only first-party pipeline, starting with JSONL durability and DuckDB query tables for aggregate reporting.
- Add cookie consent controls before enabling non-essential analytics storage.
- Update cookie and privacy policy copy to describe analytics cookies/storage, purposes, retention, and opt-out controls.
- Add an admin analytics panel with funnel, product, cart, checkout, delivery, payment, and purchase metrics.
- Report consented behavioral analytics separately from authoritative all-order business totals; use backend orders/revenue as business truth, not as a direct denominator for consented funnels.
- Add event coverage tests, ingestion tests, consent gating tests, admin authorization tests, and dashboard coverage checks against backend order counts.
- No advertising pixels, cross-site tracking, device fingerprinting, heatmaps, session replay, or profiling are introduced by this change.

## Capabilities

### New Capabilities
- `funnel-analytics`: Defines the first-party event taxonomy, frontend emission rules, backend ingestion, storage, quality checks, and funnel metrics.
- `consent-management`: Defines the site-wide cookie consent popup, consent persistence, category controls, and analytics opt-out behavior.
- `privacy-cookie-policy`: Defines updated privacy/cookie policy requirements for analytics cookies/storage and consent language.
- `admin-analytics`: Defines the admin-facing analytics review panel, dashboard metrics, filters, exports, and access controls.

### Modified Capabilities
- `global-layout`: Adds the site-wide consent popup entry point and policy/settings links.
- `admin-layout`: Adds navigation access to the analytics panel.
- `locale-ui-strings`: Adds localized strings for the consent popup, analytics settings, cookie inventory, policy copy, and admin analytics UI.

## Impact

- Backend: new analytics models, service, event ingestion route, admin analytics route, config values, startup/shutdown flushing, and analytics storage initialization.
- Frontend: new analytics client wrapper, consent state provider/component, event instrumentation across product listing, product detail, cart drawer, checkout, delivery, payment redirect, and order confirmation.
- Storage: new local analytics data path, JSONL event archive, DuckDB analytics database, schema/rebuild utilities, retention and export policy.
- Admin: new `/admin/analytics` UI and admin API integration.
- Legal/compliance: updated cookie inventory, privacy policy language, consent popup text, and withdrawal/opt-out behavior.
- GDPR: analytics data must be included in the erasure/retention model because session-linked analytics is pseudonymous personal data.
- Dependencies: likely add Python `duckdb`; avoid frontend analytics SDKs unless a future consent-approved provider replaces the first-party pipeline.
- Tests: backend unit/API tests, frontend component/integration tests, mock API analytics support, and coverage checks comparing consented analytics purchase counts/revenue with backend order counts/revenue.
