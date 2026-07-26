## Why

The AtelierMarie frontend has full page coverage but no automated end-to-end tests — all manual verification means regressions can ship silently. A Selenium test suite will provide repeatable coverage of every user-facing flow, catching breakage before it reaches production.

## What Changes

- New Selenium-based E2E test suite covering all major user flows
- Test runner configuration (pytest + selenium) with headless Chrome support
- CI-ready test execution script
- Coverage of: product browsing, cart operations, checkout flow, auth (Google OAuth mock/stub), order history, admin CRUD, reactions, and comments

## Capabilities

### New Capabilities

- `ui-e2e-test-suite`: Selenium test suite with page-object model covering all frontend flows (products, cart, checkout, orders, auth, admin, reactions, comments)

### Modified Capabilities

<!-- No existing spec-level behavior changes — this adds tests only, no production code changes -->

## Impact

- New test directory: `tests/e2e/` (Selenium, Python)
- New dev dependency: `selenium`, `webdriver-manager`, `pytest-selenium`
- Requires both backend (port 8000) and frontend (port 3000) running
- No changes to production application code
- No Layer 1 / Layer 2 boundary changes
