# Documentation File Map

Use this as the table of contents.

## Root Docs

| File | Purpose |
|---|---|
| [README.md](README.md) | Start here. Fast routing to the right doc. |
| [00-project-map.md](00-project-map.md) | Project overview, stack, layers, repo shape, change starting points. |
| [01-local-dev-and-tests.md](01-local-dev-and-tests.md) | Setup, run commands, env basics, test commands. |
| [02-backend-patterns.md](02-backend-patterns.md) | Short backend rules for routes/services/models/DB/logging. |
| [03-frontend-patterns.md](03-frontend-patterns.md) | Short frontend rules for routing/API/types/contexts/components. |

## Architecture

| File | Purpose |
|---|---|
| [architecture/01-runtime-startup.md](architecture/01-runtime-startup.md) | How FastAPI app startup, middleware, routers, lifespan, and static files work. |
| [architecture/02-layer-boundaries.md](architecture/02-layer-boundaries.md) | Layer 1 vs Layer 2 boundaries and dependency direction. |
| [architecture/03-request-and-data-flow.md](architecture/03-request-and-data-flow.md) | Main request/data flows: products, cart, checkout, payment, shipping, email, analytics. |
| [architecture/04-database-schema-guide.md](architecture/04-database-schema-guide.md) | Human map of table groups and schema rules. |
| [architecture/05-background-workers.md](architecture/05-background-workers.md) | Cleanup, email outbox, and video transcode loops. |

## Backend

| File | Purpose |
|---|---|
| [backend/01-routes-services-models.md](backend/01-routes-services-models.md) | Backend layering and examples for checkout/product listing. |
| [backend/02-config-and-environment.md](backend/02-config-and-environment.md) | Settings, env vars, production guards, session skip paths. |
| [backend/03-errors-validation-logging.md](backend/03-errors-validation-logging.md) | Error envelope, validation layers, service errors, logging rules. |
| [backend/04-testing-fixtures.md](backend/04-testing-fixtures.md) | Pytest fixtures, fake session middleware, helper use, test selection. |

## Frontend

| File | Purpose |
|---|---|
| [frontend/01-routing-layout-i18n.md](frontend/01-routing-layout-i18n.md) | Locale routing, middleware, layout provider stack, translations. |
| [frontend/02-state-api-data.md](frontend/02-state-api-data.md) | API facade, real/mock clients, types, contexts, frontend errors. |
| [frontend/03-components-pages-admin.md](frontend/03-components-pages-admin.md) | Page/component map and UI rules. |
| [frontend/04-testing-frontend.md](frontend/04-testing-frontend.md) | Vitest setup, render helpers, what to test. |

## Domains

| File | Purpose |
|---|---|
| [domains/01-product-catalog.md](domains/01-product-catalog.md) | Product listing/detail/admin CRUD/search/bilingual fields. |
| [domains/02-product-media-pipeline.md](domains/02-product-media-pipeline.md) | Image gallery, crop/upload/derivatives, product video transcode. |
| [domains/03-taxonomy-promotions-pricing.md](domains/03-taxonomy-promotions-pricing.md) | Managed taxonomy, campaigns, banner, effective price. |
| [domains/04-cart-checkout-order-flow.md](domains/04-cart-checkout-order-flow.md) | Cart, atomic checkout, order snapshots, fulfillment state machine. |
| [domains/05-payments-stripe-bank-cod.md](domains/05-payments-stripe-bank-cod.md) | COD, card/Stripe, bank transfer, payment statuses, webhooks. |
| [domains/06-shipping-couriers.md](domains/06-shipping-couriers.md) | Delivery payloads, quotes, free shipping, Econt/Speedy, tracking. |
| [domains/07-auth-sessions-admin.md](domains/07-auth-sessions-admin.md) | Anonymous sessions, Google OAuth, JWT, admin access. |
| [domains/08-email-notifications.md](domains/08-email-notifications.md) | Durable email outbox, templates, events, providers, suppression. |
| [domains/09-content-faq-about-contact.md](domains/09-content-faq-about-contact.md) | FAQ, atelier/about story, contact form, banner. |
| [domains/10-legal-privacy-gdpr.md](domains/10-legal-privacy-gdpr.md) | Legal pages, product safety, privacy/cookies, GDPR direction. |
| [domains/11-analytics-consent.md](domains/11-analytics-consent.md) | Consent-gated analytics, event validation, JSONL/DuckDB, reports. |
| [domains/12-comments-reactions.md](domains/12-comments-reactions.md) | Product comments, reactions, moderation, rate limits. |
| [domains/13-product-media-editor-and-lightbox.md](domains/13-product-media-editor-and-lightbox.md) | Dedicated crop/rotate/zoom editor, EXIF, zoom image, and unified lightbox guide. |

## Operations

| File | Purpose |
|---|---|
| [operations/01-change-playbooks.md](operations/01-change-playbooks.md) | Step-by-step playbooks for common changes. |
| [operations/02-troubleshooting.md](operations/02-troubleshooting.md) | Common failures and where to check first. |
| [operations/03-release-readiness.md](operations/03-release-readiness.md) | Pre-release checks by risk area. |

## Quick Feature Summaries

These are shorter guides from the first documentation pass. Use the deeper `domains/` docs when you need mechanics.

| File | Purpose |
|---|---|
| [features/01-products-taxonomy-media.md](features/01-products-taxonomy-media.md) | Quick product/taxonomy/media guide. |
| [features/02-cart-checkout-orders-payments.md](features/02-cart-checkout-orders-payments.md) | Quick checkout/orders/payments guide. |
| [features/03-auth-sessions-admin.md](features/03-auth-sessions-admin.md) | Quick auth/session/admin guide. |
| [features/04-shipping-delivery-couriers.md](features/04-shipping-delivery-couriers.md) | Quick shipping/courier guide. |
| [features/05-content-contact-legal.md](features/05-content-contact-legal.md) | Quick content/legal/GDPR guide. |
| [features/06-email-webhooks.md](features/06-email-webhooks.md) | Quick email/webhook guide. |
| [features/07-analytics-and-ml-boundary.md](features/07-analytics-and-ml-boundary.md) | Quick analytics/ML boundary guide. |
| [features/08-performance-quality-security.md](features/08-performance-quality-security.md) | Quick quality/security guide. |

## Reference

| File | Purpose |
|---|---|
| [reference/archive-coverage-map.md](reference/archive-coverage-map.md) | Map from archived OpenSpec changes to docs. |
| [reference/code-index.md](reference/code-index.md) | Task-to-source-file map. |
| [reference/glossary.md](reference/glossary.md) | Project terms and statuses. |
| [reference/test-map.md](reference/test-map.md) | Task-to-test-file map. |
