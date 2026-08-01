# AtelierMarie Onboarding

Last checked: 2026-07-31.

This is the current developer onboarding for the AtelierMarie repo. It favors the commands
that exist now over older archived plans/specs.

## Start Here

Use these facts as the source of truth for local development:

- Backend: FastAPI on `http://localhost:8000`.
- Backend docs: `http://localhost:8000/v1/docs`.
- Frontend: Next.js on `http://localhost:3000`.
- Storefront URLs are locale-prefixed: `http://localhost:3000/en` and `/bg`.
- Frontend mock mode is on by default: `NEXT_PUBLIC_USE_MOCK_API=true`.
- Real frontend/backend mode uses `NEXT_PUBLIC_API_URL=http://localhost:8000`.
- Python dependencies come from `pyproject.toml`, not `requirements.txt`.

## Prerequisites

Install these before setup:

- Python 3.11+. The Makefile calls `python3.11`.
- Node.js 18+. The project has also been used with Node 24.x.
- npm.
- make.
- Git.
- Optional: `ffmpeg` and `ffprobe` for product video upload/transcode work.

## First Setup

Run from the repo root:

```bash
make setup
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local
```

What this does:

- `make setup-backend` creates `.venv/` and installs `.[dev]` from `pyproject.toml`.
- `make setup-frontend` runs `npm install` in `frontend/`.
- `.env` configures the FastAPI app.
- `frontend/.env.local` configures the Next.js app.

Use Makefile targets or `.venv/bin/...` commands. You do not need to activate the venv.

## Run Locally

Terminal 1:

```bash
make dev-backend
```

Backend verification:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/v1/products | python3 -m json.tool
```

Seed sample products when you want a real local catalog:

```bash
.venv/bin/python scripts/seed_products.py
```

Terminal 2:

```bash
make dev-frontend
```

Frontend verification:

- Open `http://localhost:3000/en`.
- Open `http://localhost:3000/bg` for Bulgarian locale.
- `/` redirects to a locale based on cookie/browser language.

## Local Stripe Webhooks

Use this when testing card checkout locally. It requires the Stripe CLI and `stripe login`.

1. Get the local webhook secret:

   ```bash
   make stripe-webhook-secret
   ```

2. Copy the printed `whsec_...` value into `.env` as `STRIPE_WEBHOOK_SECRET`. Also set `STRIPE_SECRET_KEY` to a Stripe test secret key.
3. Restart the backend:

   ```bash
   make dev-backend
   ```

4. Forward Stripe events to the local backend in another terminal:

   ```bash
   make dev-stripe-webhook
   ```

The forwarder reads `.env` for `STRIPE_WEBHOOK_FORWARD_TO` and `STRIPE_WEBHOOK_EVENTS`. Defaults point to `http://127.0.0.1:8000/v1/webhooks/stripe`.

## Frontend Modes

Mock mode is best for UI work that does not need backend state:

```env
NEXT_PUBLIC_USE_MOCK_API=true
```

Real mode is required for backend integration, SQLite data, sessions, auth, admin API, and real checkout flows:

```env
NEXT_PUBLIC_USE_MOCK_API=false
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Restart the frontend dev server after changing `frontend/.env.local`.

Media behavior:

- In mock mode, `/static/*` media resolves from `frontend/public/static`.
- In real mode, `/static/*` media resolves through `NEXT_PUBLIC_MEDIA_URL` when set, otherwise `NEXT_PUBLIC_API_URL`.

## Useful Commands

```bash
make help                  # Show Makefile targets
make setup                 # Install backend + frontend dependencies
make dev-backend           # FastAPI on port 8000
make dev-frontend          # Next.js on port 3000
make stripe-webhook-secret # Print local Stripe whsec_ secret
make dev-stripe-webhook    # Forward Stripe events to local backend
make test                  # Backend pytest + frontend vitest
make test-backend          # Backend tests
make test-unit             # Backend tests excluding integration marker
make test-integration      # Real middleware/backend integration tests
make test-frontend         # Frontend vitest tests
make test-chrome-stack     # Full-stack Chrome smoke test
make lint                  # Ruff + Next lint
make format                # Ruff format + Ruff autofix
.venv/bin/python scripts/seed_products.py
```

Current lint note: `npm --prefix frontend run lint` exits successfully, but reports existing
`@next/next/no-img-element` warnings in a few image-heavy components.

## Project Map

Backend:

- `app/main.py`: FastAPI app, middleware, router registration, background tasks.
- `app/config.py`: all backend settings via pydantic-settings.
- `app/database.py`: SQLite schema, migrations, connection helpers, cleanup.
- `app/middleware/`: request ID and anonymous session middleware.
- `app/dependencies/`: FastAPI auth/session dependencies.
- `app/models/`: Pydantic request/response models.
- `app/routes/`: thin HTTP routers.
- `app/services/`: business logic.
- `app/email/`: transactional email providers, templates, rendering, redaction.
- `app/utils/`: shared helpers.

Frontend:

- `frontend/app/[locale]/`: locale-prefixed App Router pages.
- `frontend/app/design-system/`: unlocalized component gallery.
- `frontend/components/`: reusable UI and feature components.
- `frontend/contexts/`: cart, auth, admin, and cookie consent state.
- `frontend/lib/api.ts`: API facade. Components should import from here.
- `frontend/lib/api-client.ts`: real backend client.
- `frontend/lib/mock-api.ts`: mock implementation for local UI work.
- `frontend/lib/types.ts`: TypeScript API types mirroring backend models.
- `frontend/messages/en.json` and `frontend/messages/bg.json`: UI copy.
- `frontend/__tests__/`: Vitest and Testing Library coverage.

Tests and specs:

- `tests/`: backend tests.
- `tests/realapp/`: integration tests with real middleware and DB flow.
- `openspec/`: feature specs and archived implementation history.
- `docs/`, `ARCHITECTURE.md`, `DATABASE_SCHEMA.md`: deeper reference docs.

## Current Feature Surface

Public/storefront:

- Product listing, detail pages, taxonomy filters, images, and videos.
- Cart, checkout, order creation, order history, and order details.
- Delivery selection and quote calculation for Speedy/Econt flows.
- Payment methods: cash on delivery, bank transfer when configured, Stripe when configured.
- Google OAuth login, account page, and session-backed anonymous browsing.
- Product reactions and comments.
- Atelier/about content, FAQ, contact form, legal pages, banners/promotions.
- English and Bulgarian locales.

Admin:

- Dashboard and stats.
- Product CRUD, images, videos, bulk/product pricing operations.
- Order management and shipping/status updates.
- Delivery settings.
- Taxonomy management.
- FAQ and Atelier/about content management.
- Promotions and announcement banner management.
- First-party analytics dashboards and CSV export.

Backend operations:

- SQLite is the system of record.
- Session rows are created eagerly for public requests.
- Static files are served from `STATIC_FILE_PATH` under `/static`.
- Email uses a durable outbox and defaults to the console provider.
- ZeptoMail and Stripe webhooks exist when configured.
- Product video transcodes are drained by a background loop.
- First-party analytics writes JSONL and DuckDB data only when enabled.

## Environment Notes

Backend settings live in `app/config.py` and load from `.env`.

Important local backend variables:

- `ENVIRONMENT=development` keeps local cookies HTTP-compatible.
- `DATABASE_PATH=./atelier_marie.db` points at the local SQLite DB.
- `JWT_SECRET=change-me-in-production` is acceptable only for local work.
- `ADMIN_API_KEY=` disables API-key admin access until set.
- `CORS_ORIGINS=["http://localhost:3000"]` allows the local frontend.
- `STATIC_FILE_PATH=./static` serves uploaded/public product media.
- `EMAIL_PROVIDER=console` logs emails instead of sending.
- `ANALYTICS_ENABLED=false` keeps analytics ingestion disabled by default.
- Production refuses `ANALYTICS_ENABLED=true` unless `ANALYTICS_LEGAL_APPROVED=true`.
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and `STRIPE_PUBLISHABLE_KEY` configure card payments.
- Card and pay-on-delivery availability is stored in backend payment settings and managed at `/admin/settings/payments`.
- Production card payments require live Stripe keys and a live webhook secret before the admin can enable card checkout.

### Courier credentials (Speedy / Econt)

- Delivery administration is grouped under `Admin -> Delivery` in the frontend sidebar:
  - `/admin/delivery` manages enabled checkout delivery methods.
  - `/admin/delivery/econt` opens the Econt settings surface.
  - `/admin/delivery/speedy` opens the Speedy operations surface.
- Legacy direct routes `/admin/econt` and `/admin/speedy` remain available for existing links, but new admin navigation should use the grouped Delivery routes.
- `SPEEDY_API_USERNAME` / `SPEEDY_API_PASSWORD` are the API login; `SPEEDY_CLIENT_ID` is a **separate numeric** registered-client id sent as `sender.clientId` on every quote/shipment. Without it, Speedy quotes silently degrade to the flat fallback.
- Demo and prod use the **same** host (`SPEEDY_BASE_URL=https://api.speedy.bg/v1`) — only the credentials differ.
- Admins can verify Speedy configuration from `/admin/delivery/speedy`. The health check uses Speedy's safe Client Service (`POST /client`) and does not create a shipment.
- To find the right `SPEEDY_CLIENT_ID` for an account, run:

  ```bash
  .venv/bin/python scripts/fetch_speedy_client_id.py
  ```

  It lists every client on the contract; copy the numeric id of the sending account into `.env`. **Re-run this per environment** (demo, then prod) whenever the Speedy account changes.

- **Econt** auth is HTTP Basic where the **shop private key is the username and the password is empty** (`ECONT_API_USERNAME=<shopid>@<key>`, `ECONT_API_PASSWORD=`). The shop-id/private-key pair alone does *not* authenticate as `(shop_id, private_key)` — verified live.
- Econt demo vs prod differ by **both** credentials **and** the `ECONT_CALCULATE_URL` host:
  - Demo: `https://demo.econt.com/ee/services/Shipments/LabelService.createLabel.json`
  - Prod: `https://ee.econt.com/services/Shipments/LabelService.createLabel.json` (the `config.py` default — omit the override in prod, or set it explicitly).

Speedy admin operations are documented in `docs/speedy-admin-operations.md`.

Important frontend variables:

- `NEXT_PUBLIC_API_URL=http://localhost:8000`.
- `NEXT_PUBLIC_USE_MOCK_API=true` for mock mode.
- `NEXT_PUBLIC_MEDIA_URL` is optional and overrides static media origin in real mode.
- Checkout payment method availability comes from `GET /v1/settings/payments`; there is no frontend flag for enabling card or pay-on-delivery methods.
- `NEXT_PUBLIC_BANK_IBAN`, `NEXT_PUBLIC_BANK_BIC`, and `NEXT_PUBLIC_BANK_NAME` are display-only bank-transfer instruction values for existing bank-transfer orders.
- `NEXT_PUBLIC_INSTAGRAM_URL` and `NEXT_PUBLIC_TIKTOK_URL` drive public social links.

## Admin Access

Admin endpoints accept either:

- A valid JWT cookie for a user with `is_admin=true`.
- `Authorization: Bearer <ADMIN_API_KEY>` when `ADMIN_API_KEY` is set.

The first Google OAuth user created by the backend becomes admin. For local scripts, an API key is simpler:

```bash
# In .env
ADMIN_API_KEY=dev-admin-key

# After restarting the backend
curl -H "Authorization: Bearer dev-admin-key" \
  http://localhost:8000/v1/admin/products | python3 -m json.tool
```

## Backend Coding Rules

- Keep routes thin: HTTP parsing, dependencies, status codes, response models.
- Put business rules in services.
- Use Pydantic 2 models for validated inputs/outputs.
- Read settings through `app.config.get_settings()`, not direct `os.environ` in app code.
- Store prices as integer cents using `price_cents`.
- Product IDs are text slugs/SKUs, not integer DB IDs.
- SQLite is the production data store for e-commerce state.
- Wrap stock/order/payment mutations in explicit transactions.
- Use the standard error envelope: `{"error":{"code":...,"message":...,"details":...}}`.
- Keep transactional email in Layer 1. It must not depend on analytics.

## Frontend Coding Rules

- Import API functions from `frontend/lib/api.ts`, not directly from `mock-api.ts` or `api-client.ts`.
- Keep API types in `frontend/lib/types.ts` aligned with backend Pydantic models.
- Put localized routes under `frontend/app/[locale]/`.
- Put UI copy in both `frontend/messages/en.json` and `frontend/messages/bg.json`.
- Use `frontend/lib/media.ts` for product/static media URLs.
- Keep mock mode working for ordinary storefront UI development.
- Restart Next.js after changing `NEXT_PUBLIC_*` variables.

## Analytics Rules

Analytics is implemented, but consent-gated and off by default.

- Public ingestion routes: `/v1/analytics/consent` and `/v1/analytics/events`.
- Admin routes: `/v1/admin/analytics/*`.
- Storage: JSONL source log plus DuckDB query tables.
- Do not send PII in analytics properties.
- Do not add analytics work that blocks checkout, order creation, email, or admin operations.
- Production analytics requires explicit `ANALYTICS_LEGAL_APPROVED=true`.

## Common Checks

Run these before handing off backend changes:

```bash
make test-backend
.venv/bin/ruff check .
```

Run these before handing off frontend changes:

```bash
npm --prefix frontend run typecheck
make test-frontend
npm --prefix frontend run lint
```

Run this before handing off cross-stack checkout/cart/admin changes:

```bash
make test
make test-chrome-stack
```

## Troubleshooting

Backend says port 8000 is in use:

```bash
lsof -i :8000
```

Then stop the old process or run uvicorn manually on another port and update `NEXT_PUBLIC_API_URL`.

Frontend still calls the mock API:

- Check `frontend/.env.local`.
- Set `NEXT_PUBLIC_USE_MOCK_API=false`.
- Restart `make dev-frontend`.

No products in real mode:

```bash
.venv/bin/python scripts/seed_products.py
```

Admin request returns 401:

- Set `ADMIN_API_KEY` in `.env`.
- Restart the backend.
- Send `Authorization: Bearer <same value>`.

Google login says auth is not configured:

- Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REDIRECT_URI`.
- Keep `FRONTEND_URL=http://localhost:3000` unless testing another frontend origin.

Product videos fail locally:

- Install `ffmpeg` and `ffprobe`.
- Confirm `FFMPEG_PATH` and `FFPROBE_PATH` resolve on your PATH.
- Keep `VIDEO_UPLOAD_TEMP_PATH` outside `STATIC_FILE_PATH`.

Analytics returns validation/disabled errors:

- Confirm `ANALYTICS_ENABLED=true` only when you are intentionally testing analytics.
- Record consent before sending events.
- Keep event properties on the allowlist and free of PII.

## Good First Tasks

Start with tasks that are small and easy to verify:

- Add or improve a frontend component test.
- Add a backend service test for an edge case.
- Improve empty/loading/error states in a page.
- Tighten localized copy in both `en.json` and `bg.json`.
- Add a focused admin workflow polish item.
- Update stale docs when code and docs disagree.

Avoid these as first tasks:

- Payment provider behavior.
- Session/auth rotation.
- SQLite schema migrations.
- Analytics consent/legal behavior.
- Product video processing.
- Cross-stack checkout changes.
