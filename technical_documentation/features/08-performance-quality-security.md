# Performance, Quality, And Security

Use this when cleaning up technical debt, hardening behavior, or reviewing risky changes.

## Why This Exists

The archive has several hardening changes because the project grew fast. The current standards are not fancy. They are there to stop boring production bugs.

## Performance Rules

- Product listing should stay fast.
- Avoid N+1 queries. Batch load related rows like images, videos, order items, labels.
- Use FTS5 search and sanitize search input.
- Clamp pagination.
- Memoize high-churn frontend context values.
- Use `next/image` and existing media helpers for product/user images.

## Checkout/Concurrency Rules

- Stock-changing checkout uses `BEGIN IMMEDIATE`.
- DB constraint `stock >= 0` is the last line of defense.
- Background cleanup task lifecycle is managed by app lifespan.
- Webhook processing is idempotent.
- Email outbox prevents double-sent rows with DB-level guards where appropriate.

## Validation Rules

- Product IDs are slug-like strings.
- Product names cannot be blank.
- Prices are positive integer cents.
- Stock is non-negative.
- Cart quantity has bounds.
- Pagination has bounds.
- CSV import validates values before write.
- Free text is sanitized where it can render back to users.

## Error Handling Rules

- Use custom service exceptions for expected failures.
- Route layer maps exceptions to HTTP codes.
- Use the standard error envelope.
- Catch specific exceptions where possible.
- Chain exceptions when wrapping.
- Log useful context without PII.

## Security Rules

- No f-string SQL.
- Admin API key comparison is constant-time.
- Empty admin key disables key auth.
- Production refuses weak admin/JWT defaults.
- Stripe and ZeptoMail webhooks verify raw body signatures.
- Logs must avoid raw emails, phones, addresses, notes, and raw webhook payloads.
- Rate-limit sensitive endpoints where implemented: auth, checkout, comments/reactions, webhooks by signature/body cap.

## Frontend Quality Rules

- Use shared UI components.
- Use shared status maps.
- Use `cn()` for class composition.
- Keep loading/error/empty states visible.
- Preserve form input on backend validation errors.
- Do not rely on redirects as proof of payment.

## Test Fixture Rules

- Shared fixtures live in `conftest.py`.
- Many route tests use fake session middleware for speed.
- Real middleware behavior belongs in `tests/realapp/`.
- Use helper functions for session/product setup instead of copy-pasted inserts.
- Keep route tests focused on HTTP behavior and service tests focused on business rules.

## Review Checklist

- Could this break checkout if Stripe/email/courier/analytics is down?
- Could two users buy the last item at the same time?
- Did a frontend total become trusted as money truth?
- Did we add a new status without updating labels/tests?
- Did we add a user-visible string in both languages?
- Did we log PII?
- Did mock API drift from backend model?
- Did a migration handle old DBs and fresh DBs?

