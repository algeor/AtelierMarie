# Local Dev And Tests

This is the short version. Use `make` unless you need one specific command.

## First Setup

```bash
make setup
```

This installs backend and frontend dependencies.

## Run The App

Backend:

```bash
make dev-backend
```

Frontend:

```bash
make dev-frontend
```

Default URLs:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

## Mock API Mode

The frontend can run without the backend.

Set this in `frontend/.env.local`:

```text
NEXT_PUBLIC_USE_MOCK_API=true
```

Use real backend calls with:

```text
NEXT_PUBLIC_USE_MOCK_API=false
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Backend Env Basics

Copy `.env.example` to `.env` when needed.

Important settings:

- `DATABASE_PATH`: SQLite file path. Defaults to `./atelier_marie.db`.
- `ADMIN_API_KEY`: admin API key, required in production.
- `JWT_SECRET`: must not be the dev default in production.
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`: card payments.
- `BANK_IBAN`, `BANK_BIC`, `BANK_NAME`: bank transfer instructions.
- `EMAIL_PROVIDER`: `console` or `zeptomail`.
- `ANALYTICS_ENABLED`: false by default.
- `ANALYTICS_LEGAL_APPROVED`: must be true before production analytics can be enabled.
- `SPEEDY_*`, `ECONT_*`: courier pricing/shipping credentials.

## Local Stripe Webhook Forwarding

For local card checkout work, install the Stripe CLI and run `stripe login` once.

```bash
make stripe-webhook-secret
```

Copy the printed `whsec_...` value into `.env` as `STRIPE_WEBHOOK_SECRET`, set `STRIPE_SECRET_KEY` to a test secret key, then restart `make dev-backend`.

Forward events in a separate terminal:

```bash
make dev-stripe-webhook
```

Defaults come from `.env` when present:

- `STRIPE_WEBHOOK_FORWARD_TO=http://127.0.0.1:8000/v1/webhooks/stripe`
- `STRIPE_WEBHOOK_EVENTS=checkout.session.completed,payment_intent.payment_failed,checkout.session.expired,charge.refunded`

## Test Commands

All tests:

```bash
make test
```

Backend only:

```bash
make test-backend
```

Frontend only:

```bash
make test-frontend
```

Focused backend test:

```bash
.venv/bin/pytest tests/test_order_service.py -v --tb=short
```

Focused frontend test:

```bash
cd frontend && npx vitest run __tests__/app/checkout.test.tsx
```

Lint everything:

```bash
make lint
```

Format Python:

```bash
make format
```

## Pick The Right Test

- Changed a service: run that service test file.
- Changed a route: run route tests plus related service tests.
- Changed session middleware: run `tests/realapp/` session tests too.
- Changed checkout/order/payment/shipping: run checkout/order/payment/shipping tests. This area is connected.
- Changed frontend component behavior: run the matching Vitest file.
- Changed i18n keys: run i18n rendering tests and the page test that uses the keys.

## Common Gotchas

- Do not use `source .venv/bin/activate` in scripts. Existing project guidance prefers `.venv/bin/...` or `make`.
- Frontend mock mode can hide backend contract bugs. If you changed API shape, test real backend mode too.
- SQLite migrations run from `app/database.py` during startup. If a column exists locally, still test fresh DB behavior.
- Analytics can be off. Do not write a feature that only works when analytics storage exists.
- Stripe webhooks need raw body signature verification. Do not parse first, verify later.
