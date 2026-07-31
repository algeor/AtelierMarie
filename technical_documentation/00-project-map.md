# Project Map

Atelier Marie is a luxury candle e-commerce app.

It has one serious job: sell candles reliably. Analytics and ML ideas exist, but they must never become required for the store to work.

## Stack

- Backend: FastAPI, Python 3.11, Pydantic 2, SQLite WAL.
- Frontend: Next.js App Router, TypeScript, Tailwind, `next-intl`.
- Auth: anonymous session cookie first, optional Google OAuth, JWT cookie for logged-in users.
- Payments: COD, card through Stripe Checkout, bank transfer.
- Shipping: structured delivery selection, Econt and Speedy pricing, Speedy waybill support.
- Email: durable outbox, Jinja2 text templates, console or ZeptoMail provider.
- Analytics: first-party, consent-gated, off by default, SQLite/JSONL plus DuckDB for reports.

## The Two Layers

### Layer 1: production e-commerce

This is the real shop.

It includes products, cart, checkout, orders, auth, admin, payments, shipping, email, FAQ, about/story pages, contact, legal pages, media, promotions, and taxonomy.

Rules:

- It uses SQLite as the system of record.
- It should stay fast.
- It must work if analytics is disabled.
- It must not import or require ML sandbox code.
- It should treat external services as optional or retryable where possible.

### Layer 2: analytics and ML sandbox

This is learning/measurement infrastructure.

Rules:

- Analytics is consent-gated and disabled by default.
- Analytics failures must not block storefront or checkout.
- ML recommendations are deferred. Treat old ML-first specs as historical context, not live rules.

## Repo Shape

```text
app/                      FastAPI backend
  main.py                 App setup, routers, lifespan background jobs
  config.py               Environment settings, no raw os.getenv in app code
  database.py             SQLite schema, startup migrations, WAL setup
  models/                 Pydantic request/response models
  routes/                 Thin HTTP layer
  services/               Business logic
  email/                  Templates, renderer, providers, redaction
  middleware/             Session and request id middleware
  dependencies/           FastAPI Depends helpers
  utils/                  Shared helpers only

frontend/                 Next.js app
  app/[locale]/           Locale-prefixed pages: /en/... and /bg/...
  components/             UI, layout, product, cart, checkout, admin, etc.
  contexts/               Auth, cart, admin, cookie consent
  lib/                    API clients, types, tracking, utility functions
  messages/               en/bg translation files
  i18n/                   next-intl routing and request setup

tests/                    Backend pytest tests
tests/realapp/            Real middleware integration tests
docs/                     Existing architecture and schema docs
openspec/changes/archive/ Historical implemented/superseded OpenSpec changes
technical_documentation/  This folder
```

## Normal Request Flow

Example: checkout.

1. Frontend submits `POST /v1/orders` with cart session cookie.
2. Route validates HTTP shape and resolves session/user/locale.
3. Service opens a `BEGIN IMMEDIATE` transaction.
4. Service validates stock and active products.
5. Service computes effective item prices and shipping total.
6. Service creates order rows and immutable item snapshots.
7. Service decrements stock and clears cart.
8. Service queues email in the outbox.
9. Service commits.
10. Optional systems run after or around that core path: Stripe session creation, analytics event recording, email sweeper.

## Where To Start For A Change

- API field changed: backend `app/models/*`, frontend `frontend/lib/types.ts`, API client/mock API, tests.
- Business rule changed: backend service first, route second, tests third.
- New admin field: database schema, Pydantic admin model, service, admin route, `ProductForm` or admin page, frontend type.
- New storefront copy: `frontend/messages/en.json`, `frontend/messages/bg.json`, page/component.
- Checkout/payment/shipping: read feature docs first. These have the highest blast radius.

## Things That Are Historical

Some archive specs were written during an early "ML-first" phase. The current repo is Layer-1-first. Do not revive old requirements that make the shop depend on analytics, DuckDB, recommendation jobs, or event ingestion.

