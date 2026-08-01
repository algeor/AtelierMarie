## Why

AtelierMarie already collects structured courier delivery details, but Econt fulfillment is still manual. This change turns Econt into a first-class fulfillment integration across checkout, admin settings, labels, tracking, and order operations.

## What Changes

- Add admin-managed Econt settings for environment, credentials, shop id, sender origin, default shipment options, payment-side rules, and feature toggles.
- Add an Econt Delivery API client for `updateOrder`, `createAWB`, `getTrace`, and `deleteLabel` with typed models, timeouts, error mapping, redacted logging, and test fakes.
- Preserve Econt `officeCode` in courier office data separately from internal `office_id`.
- Improve customer checkout for Econt office/locker selection, optional Econt Office Locator support, final delivery state, and post-purchase tracking details.
- Add admin fulfillment actions to sync an order, create AWB/label, open/download PDF labels, delete labels where safe, refresh tracking, and mark orders shipped from returned shipment numbers.
- Persist courier shipment metadata, request/response snapshots, label URLs, trace events, last sync state, and retryable error state on orders.
- Keep external Econt API calls outside the atomic checkout transaction and make failures actionable for admins without leaking raw courier errors to customers.
- Map payment methods correctly: COD orders request Econt COD; card and bank-transfer orders do not.
- Add backend and frontend tests for configuration, client behavior, shipment service, admin routes, checkout serialization, UI states, and failure modes.

## Capabilities

### New Capabilities

- `econt-integration-settings`: Admin configuration and operational health for the Econt integration.
- `econt-fulfillment`: Econt order sync, label/AWB creation, label deletion, tracking refresh, payload/error persistence, and admin fulfillment actions.

### Modified Capabilities

- `courier-offices-data`: Preserve courier-native Econt office codes and expose them safely to checkout/order submission.
- `courier-delivery`: Econt-specific customer delivery behavior, optional office locator integration, and validated Econt destination payloads.
- `checkout-flow`: Store enough Econt delivery metadata at order creation to support later label generation without re-asking the customer.
- `checkout-ui`: Improve Econt customer delivery selection and show Econt-specific readiness/tracking details.
- `admin-orders`: Add Econt fulfillment controls, label status, PDF links, tracking refresh, and retryable courier error display.
- `order-management`: Persist courier shipment metadata and keep order status/tracking transitions consistent with Econt fulfillment events.
- `order-tracking`: Refresh and display Econt trace events from the courier API.
- `external-call-resilience`: Apply the established timeout/circuit-breaker/error-redaction rules to Econt API calls.

## Impact

- Backend: `app/config.py`, `app/database.py`, delivery/order models, `delivery_service`, new Econt client/service modules, admin/delivery/order routes, exception mapping, logging, tests.
- Frontend: checkout delivery components, admin settings pages, admin order detail fulfillment actions, order confirmation/detail tracking views, API client/types, i18n strings, tests.
- Data: normalized Econt office JSON gains `code`; orders gain courier shipment metadata and Econt sync/error snapshots.
- External systems: Econt Delivery production/demo API, optional Econt Office Locator iframe, and existing email/payment flows.
- Dependencies: uses existing `httpx`, `structlog`, Pydantic, SQLite migration style, and OpenSpec patterns; no new runtime dependency is expected.
