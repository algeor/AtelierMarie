# Frontend Testing

Frontend tests use Vitest, jsdom, and Testing Library.

## Main Files

- `frontend/vitest.config.ts`: test config and alias.
- `frontend/__tests__/setup.ts`: jsdom setup and missing browser API stubs.
- `frontend/__tests__/test-utils.tsx`: render helpers with `next-intl`.
- `frontend/__tests__/*`: component, page, context, and lib tests.

## Test Environment

- Environment: `jsdom`.
- Globals: enabled.
- Alias: `@` maps to `frontend/`.
- Setup adds jest-dom matchers.
- Setup stubs localStorage, matchMedia, ResizeObserver, object URLs.

## Render With Translations

Use `renderWithIntl` for components using `useTranslations()`.

It wraps the component in `NextIntlClientProvider` with English messages.

If a component depends on contexts, wrap those too.

## What To Test

| Change | Test focus |
|---|---|
| API facade | correct path, mock/real behavior where practical. |
| Context | hydrate, success, failure, events like `session-rotated`. |
| Checkout | method selection, delivery data, error preservation, redirect/status behavior. |
| Product UI | price display, media display, loading/error states. |
| Admin form | validation, payload shape, save state, field presence. |
| i18n | both language catalogs contain keys; rendered copy appears. |
| Legal pages | required sections/links exist. |

## Mocking API Calls

Prefer mocking `@/lib/api` at the module boundary for component/page tests.

Why:

- tests stay focused on component behavior
- real fetch behavior belongs in API client tests
- backend contracts are still covered by backend tests

## Common Test Gaps

- Only testing English when Bulgarian string length affects layout.
- Updating backend model but not mock API test data.
- Testing happy path only for checkout/payment.
- Forgetting session rotation behavior after login/logout.
- Rendering admin UI without asserting backend error display.

## Commands

All frontend tests:

```bash
make test-frontend
```

Focused test:

```bash
cd frontend && npx vitest run __tests__/app/checkout.test.tsx
```

Watch mode:

```bash
cd frontend && npx vitest
```

