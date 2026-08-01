# Runtime Startup

This explains what happens when `app.main:create_app()` and the FastAPI lifespan run.

## The Short Version

App startup does four jobs:

1. Load settings from env.
2. Configure FastAPI, middleware, routers, and static files.
3. Initialize SQLite schema during lifespan startup.
4. Start background loops for cleanup, email, and video work.

## Main Files

- `app/main.py`: app factory, lifespan, background loops, router registration.
- `app/config.py`: Pydantic Settings.
- `app/database.py`: schema creation, connection helpers, cleanup.
- `app/logging_config.py`: structlog setup.
- `app/middleware/session.py`: session cookie handling.
- `app/middleware/request_id.py`: request correlation ID.

## Create App Flow

`create_app()` builds the app object. It does not do all runtime work itself.

Flow:

1. `settings = get_settings()` reads cached Pydantic settings.
2. Video temp path is checked so raw upload staging is not inside public `/static`.
3. FastAPI app is created with docs at `/v1/docs` and OpenAPI at `/v1/openapi.json`.
4. Middleware is added.
5. Health endpoints are registered.
6. `/static` is mounted.
7. All routers are included under `/v1/...`.
8. Global exception handlers are registered.

## Middleware Order

Starlette middleware runs last-added first on incoming requests.

Current setup:

1. `CORSMiddleware` is outermost. It handles preflight before session creation.
2. `RequestIdMiddleware` adds request correlation.
3. `SessionMiddleware` runs closest to routes and attaches session state.

Practical effect:

- Browser preflight should not create sessions.
- Request IDs are available around session work.
- Routes can use `require_session` after middleware attaches `request.state.session_id`.

## Lifespan Startup

The lifespan function runs when the ASGI app starts.

It does this:

1. Configures logging for the current environment.
2. Calls `init_db(settings.database_url)`.
3. Initializes analytics storage only if analytics is enabled.
4. Ensures static directories exist.
5. Ensures video temp directory exists and is private.
6. Starts three background loops:
   - runtime cleanup
   - email outbox drain
   - product video transcode drain

## Lifespan Shutdown

On shutdown:

1. If analytics is enabled, JSONL events are loaded to DuckDB.
2. Background tasks are cancelled.
3. Each task gets a short timeout to stop.

## Router Map

Current router prefixes:

| Prefix | Router | Purpose |
|---|---|---|
| `/v1/products` | `products`, `reactions`, `comments` | Product catalog plus social features. |
| `/v1/cart` | `cart` | Session cart. |
| `/v1/orders` | `orders` | Checkout, order history, retry card payment. |
| `/v1/auth` | `auth` | Google OAuth, current user, logout. |
| `/v1/admin` | `admin` | Admin products, orders, dashboard, analytics, delivery. |
| `/v1/about` | `about.public_router` | Public atelier story content. |
| `/v1/admin/about` | `about.admin_router` | Admin atelier story editing. |
| `/v1/taxonomy` | `taxonomy.public_router` | Public product taxonomy. |
| `/v1/admin/taxonomy` | `taxonomy.admin_router` | Admin taxonomy CRUD. |
| `/v1/faq` | `faq.public_router` | Public FAQ. |
| `/v1/admin/faq` | `faq.admin_router` | Admin FAQ editing. |
| `/v1/admin/promotions` | `promotions.admin_router` | Campaigns and banner admin. |
| `/v1/promotions` | `promotions.public_router` | Public banner. |
| `/v1/contact` | `contact` | Contact form. |
| `/v1/locale` | `locale` | Session locale preference. |
| `/v1/delivery` | `delivery` | Delivery settings, places, offices, quotes. |
| `/v1/analytics` | `analytics` | Consent and event ingestion. |
| `/v1/webhooks` | `webhooks` | Stripe and ZeptoMail webhooks. |

## Startup Gotchas

- `create_app()` is called at module import as `app = create_app()`. Tests sometimes call it too.
- Settings are cached. Tests should clear `get_settings.cache_clear()` after env changes.
- Static media is served from source checkout paths. If packaging as a wheel, templates/static assumptions need review.
- Background loops are per worker. Outbox claims exist because more than one worker can try to send.

