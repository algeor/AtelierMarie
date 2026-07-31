# Payment Integration Test Plan

## Local Stripe CLI Webhook Verification

Date: 2026-07-31

Environment:
- Backend: temporary local app on `http://127.0.0.1:8765`
- Database: isolated SQLite DB at `/tmp/ateliermarie-stripe-cli-verify.db`
- Stripe CLI: `stripe version 1.45.0`
- Webhook secret: provided by `stripe listen --print-secret` and configured in the backend environment; secret value intentionally omitted.

Commands run:

```bash
make stripe-webhook-secret
DATABASE_PATH=/tmp/ateliermarie-stripe-cli-verify.db \
  STRIPE_WEBHOOK_SECRET=<stripe-listener-secret> \
  STRIPE_SECRET_KEY=<test-secret-key> \
  uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8765
STRIPE_WEBHOOK_FORWARD_TO=http://127.0.0.1:8765/v1/webhooks/stripe \
  make dev-stripe-webhook
stripe trigger checkout.session.completed
```

Observed result:
- Stripe CLI reported `Trigger succeeded!`.
- Stripe listener forwarded `checkout.session.completed` to `POST /v1/webhooks/stripe`.
- Listener received `[200] POST http://127.0.0.1:8765/v1/webhooks/stripe`.
- Backend logged `stripe_payment_succeeded_ignored` because the generated Stripe fixture did not include a local order id, then returned `200 OK` as expected for a valid signed webhook.

Coverage notes:
- Local CLI verifies signed delivery reaches the app and returns 200.
- Automated tests cover mutation-specific webhook behavior for matching local orders: signature rejection, idempotency, `checkout.session.completed`, `checkout.session.expired`, `payment_intent.payment_failed`, late-success review handling, and refund audit-only behavior.
