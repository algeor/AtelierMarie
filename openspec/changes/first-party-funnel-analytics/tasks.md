## 1. Configuration and Dependencies

- [x] 1.1 Add backend analytics configuration values for enabled flag, data directory, JSONL path, DuckDB path, consent version, batch size, retention days, and consented-order delivery tolerance
- [x] 1.2 Add the Python `duckdb` dependency and lock/update the project environment
- [x] 1.3 Add safe default config so analytics collection is disabled unless explicitly enabled
- [x] 1.4 Add test configuration helpers for isolated temporary analytics storage

## 2. Backend Event Contract

- [x] 2.1 Create backend analytics event type enum for `product_view`, `listing_filter`, `add_to_cart`, `cart_open`, `checkout_start`, `delivery_selected`, `shipping_quote_selected`, `order_submit`, `payment_redirect`, and `purchase_confirmed`
- [x] 2.2 Create Pydantic request models for single-event and batched analytics ingestion
- [x] 2.3 Define event-specific property allowlists and maximum lengths
- [x] 2.4 Reject PII-like keys and unknown metadata keys in analytics payloads
- [x] 2.5 Derive `session_id` from request state instead of trusting client-submitted session IDs
- [x] 2.6 Attach authenticated `user_id` when a valid user session exists without requiring login for anonymous events
- [x] 2.7 Add idempotency validation using `event_id` scoped to session

## 3. Backend Storage Pipeline

- [x] 3.1 Create `app/services/analytics_service.py` for validation, append, flush, and query orchestration
- [x] 3.2 Implement append-only JSONL event writing with crash-safe line writes
- [x] 3.3 Implement DuckDB schema initialization for events and delivery health tables
- [x] 3.4 Implement JSONL-to-DuckDB loading with duplicate protection
- [x] 3.5 Implement rebuild utility to recreate DuckDB tables from JSONL
- [x] 3.6 Implement retention cleanup or retention reporting according to configured retention days
- [x] 3.7 Ensure analytics write failures are logged but do not fail storefront requests

## 4. Backend Public Ingestion API

- [x] 4.1 Add `POST /v1/analytics/events` route
- [x] 4.2 Enforce batch size, payload size, timestamp, event type, and property validation
- [x] 4.3 Return HTTP 202 for accepted events
- [x] 4.4 Return HTTP 422 for invalid events without persisting them
- [x] 4.5 Track accepted, rejected, duplicate, and validation-failure counters
- [x] 4.6 Register the analytics route in FastAPI application startup
- [x] 4.7 Add startup/shutdown hooks to initialize storage and flush pending analytics work

## 5. Backend Purchase Confirmation and Coverage

- [x] 5.1 Capture analytics consent state at successful backend order creation for every payment method
- [x] 5.2 Emit or record `purchase_confirmed` at successful backend order creation when analytics consent is present
- [x] 5.3 Ensure failed checkout/order attempts never create purchase confirmations
- [x] 5.4 Add backend analytics queries for authoritative order totals and consented analytics purchase totals by date range
- [x] 5.5 Add coverage and consented-order delivery delta calculations between analytics purchases and backend order records

## 6. Admin Analytics API

- [x] 6.1 Add admin-only analytics summary endpoint
- [x] 6.2 Add admin-only funnel metrics endpoint
- [x] 6.3 Add admin-only product analytics endpoint
- [x] 6.4 Add admin-only checkout/delivery/payment analytics endpoint
- [x] 6.5 Add admin-only event delivery health endpoint
- [x] 6.6 Add admin-only aggregate CSV export endpoint
- [x] 6.7 Ensure every analytics admin endpoint uses existing admin authorization
- [x] 6.8 Ensure analytics responses contain no customer PII

## 7. Consent Management Frontend

- [x] 7.1 Create frontend consent model and helpers for reading/writing the consent preference cookie
- [x] 7.2 Create `CookieConsentProvider` or equivalent client component for consent state
- [x] 7.3 Create cookie consent popup with accept analytics, necessary only, and manage preferences controls
- [x] 7.4 Add keyboard accessibility and focus behavior for the consent popup
- [x] 7.5 Add consent version checking so outdated consent choices resurface the popup
- [x] 7.6 Add cookie settings entry point from footer or Cookie Policy page
- [x] 7.7 Clear pending analytics queue when a visitor withdraws analytics consent
- [x] 7.8 Verify consent popup does not render in admin layout

## 8. Privacy and Cookie Policy Copy

- [x] 8.1 Update English cookie inventory with the consent preference cookie
- [x] 8.2 Update Bulgarian cookie inventory with the consent preference cookie
- [x] 8.3 Update cookie policy copy to explain first-party analytics and analytics use of the session cookie after consent
- [x] 8.4 Replace current no-analytics copy when analytics is enabled
- [x] 8.5 Update privacy policy copy with analytics purpose, data categories, retention, consent basis, and withdrawal mechanism
- [x] 8.6 Add owner/legal review note before production analytics enablement
- [x] 8.7 Add tests that policy pages no longer claim there is no analytics when analytics copy is enabled

## 9. Frontend Analytics Client

- [x] 9.1 Create `frontend/lib/analytics.ts` with typed event helpers and event ID generation
- [x] 9.2 Implement in-memory event queue and flush behavior
- [x] 9.3 Use `navigator.sendBeacon()` for unload-safe delivery
- [x] 9.4 Add `fetch(..., { keepalive: true })` fallback when `sendBeacon` is unavailable
- [x] 9.5 Gate all event sends on analytics consent
- [x] 9.6 Add duplicate-safe retry behavior for transient network failures
- [x] 9.7 Add mock API support for analytics ingestion in frontend tests

## 10. Storefront Event Instrumentation

- [x] 10.1 Instrument product detail page `product_view`
- [x] 10.2 Instrument product listing filters with `listing_filter`
- [x] 10.3 Instrument add-to-cart flows with `add_to_cart`
- [x] 10.4 Instrument cart drawer open with `cart_open`
- [x] 10.5 Instrument checkout page entry with `checkout_start`
- [x] 10.6 Instrument delivery method/courier selection with `delivery_selected`
- [x] 10.7 Instrument shipping quote choice with `shipping_quote_selected` only when selectable shipping quotes exist
- [x] 10.8 Instrument order submission attempt with `order_submit`
- [x] 10.9 Instrument card payment handoff with `payment_redirect`
- [x] 10.10 Instrument or record `purchase_confirmed` only after successful backend order creation
- [x] 10.11 Ensure instrumentation sends no email, phone, address, name, notes, or raw payment details

## 11. Admin Analytics Frontend

- [x] 11.1 Add Analytics item to admin sidebar navigation
- [x] 11.2 Create `/admin/analytics` page shell with date range controls
- [x] 11.3 Add summary metric cards for consented sessions, accepted events, conversion, orders, revenue, and delivery health
- [x] 11.4 Add funnel table/chart with counts and step conversion percentages
- [x] 11.5 Add product analytics table with views, add-to-cart, purchases, revenue, and conversion
- [x] 11.6 Add checkout/delivery/payment section with method/courier and payment redirect metrics
- [x] 11.7 Add order coverage display and consented-order delivery warning when eligible analytics purchases are missing beyond tolerance
- [x] 11.8 Add CSV export controls for aggregate reports
- [x] 11.9 Add loading, empty, and error states for all analytics panels
- [x] 11.10 Keep layout responsive without overlapping text or controls on mobile/tablet/desktop

## 12. Localization

- [x] 12.1 Add English consent popup and settings strings
- [x] 12.2 Add Bulgarian consent popup and settings strings
- [x] 12.3 Add English admin analytics labels, filters, warnings, empty states, and export strings
- [x] 12.4 Add Bulgarian admin analytics labels, filters, warnings, empty states, and export strings
- [x] 12.5 Add English and Bulgarian privacy/cookie analytics policy strings
- [x] 12.6 Add tests that consent and admin analytics surfaces render localized text through message files

## 13. Backend Tests

- [x] 13.1 Test valid single-event ingestion returns HTTP 202 and writes JSONL
- [x] 13.2 Test valid batch ingestion returns HTTP 202 and writes all events
- [x] 13.3 Test invalid event type, unknown metadata, PII keys, oversized payload, and oversized batch return HTTP 422
- [x] 13.4 Test duplicate `event_id` is not double-counted
- [x] 13.5 Test DuckDB rebuild from JSONL preserves counts
- [x] 13.6 Test analytics write failures do not break cart, checkout, or order APIs
- [x] 13.7 Test admin analytics endpoints require admin access
- [x] 13.8 Test delivery health metrics report accepted, rejected, duplicate, and validation failure counts
- [x] 13.9 Test order coverage and consented-order delivery warning against seeded backend orders

## 14. Frontend Tests

- [x] 14.1 Test consent popup appears without consent and hides after choice
- [x] 14.2 Test necessary-only choice prevents analytics requests
- [x] 14.3 Test accepted analytics choice allows analytics requests
- [x] 14.4 Test withdrawing consent stops sends and clears queued events
- [x] 14.5 Test each required storefront event is emitted from its user interaction when consent is accepted
- [x] 14.6 Test event payloads exclude PII fields from checkout and delivery flows
- [x] 14.7 Test admin analytics page renders summary, funnel, product, coverage, loading, empty, and error states
- [x] 14.8 Test admin sidebar includes Analytics link and active state
- [x] 14.9 Test responsive consent popup and admin analytics layout at mobile and desktop widths

## 15. Verification and Rollout

- [x] 15.1 Run backend tests covering analytics ingestion, storage, admin APIs, coverage, and consented-order delivery checks
- [x] 15.2 Run frontend unit/component tests covering consent, instrumentation, policy pages, and admin analytics
- [x] 15.3 Run lint/build checks for backend and frontend
- [x] 15.4 Manually inspect JSONL event output in development with analytics accepted
- [x] 15.5 Manually verify no events are written when analytics consent is rejected
- [x] 15.6 Manually verify admin dashboard order coverage and consented-order delivery checks against backend order counts in a seeded dataset
- [ ] 15.7 Confirm privacy/cookie copy has owner/legal approval before enabling analytics in production
- [ ] 15.8 Enable analytics in production only after consent UI, policy copy, and admin monitoring are live
