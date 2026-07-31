# Archive Coverage Map

This file proves the archive was covered.

Source folder: `openspec/changes/archive`.

Coverage style: the docs do not repeat every old requirement line-by-line. They consolidate the archive into current developer guidance. When archived specs conflict with current code, the topic docs use current code names and call out the safer rule.

For deeper mechanics, prefer the `domains/`, `architecture/`, `backend/`, and `frontend/` docs. The older `features/` docs are quick summaries.

## Deep Landing Pages

| Area | Deep docs |
|---|---|
| Products/media/taxonomy/pricing | [domains/01-product-catalog.md](../domains/01-product-catalog.md), [domains/02-product-media-pipeline.md](../domains/02-product-media-pipeline.md), [domains/13-product-media-editor-and-lightbox.md](../domains/13-product-media-editor-and-lightbox.md), [domains/03-taxonomy-promotions-pricing.md](../domains/03-taxonomy-promotions-pricing.md) |
| Cart/checkout/orders/payments | [domains/04-cart-checkout-order-flow.md](../domains/04-cart-checkout-order-flow.md), [domains/05-payments-stripe-bank-cod.md](../domains/05-payments-stripe-bank-cod.md) |
| Shipping/couriers | [domains/06-shipping-couriers.md](../domains/06-shipping-couriers.md) |
| Auth/sessions/admin | [domains/07-auth-sessions-admin.md](../domains/07-auth-sessions-admin.md) |
| Email/webhooks | [domains/08-email-notifications.md](../domains/08-email-notifications.md), [domains/05-payments-stripe-bank-cod.md](../domains/05-payments-stripe-bank-cod.md) |
| Content/legal/GDPR | [domains/09-content-faq-about-contact.md](../domains/09-content-faq-about-contact.md), [domains/10-legal-privacy-gdpr.md](../domains/10-legal-privacy-gdpr.md) |
| Analytics/ML boundary | [domains/11-analytics-consent.md](../domains/11-analytics-consent.md), [architecture/02-layer-boundaries.md](../architecture/02-layer-boundaries.md) |
| Quality/security/testing | [backend/03-errors-validation-logging.md](../backend/03-errors-validation-logging.md), [backend/04-testing-fixtures.md](../backend/04-testing-fixtures.md), [operations/03-release-readiness.md](../operations/03-release-readiness.md) |

## Coverage Table

| Archived change | Main topic | Covered in |
|---|---|---|
| `2026-07-07-api-contracts-shared-setup` | Pydantic contracts, frontend scaffold, API/model mirroring | [00-project-map.md](../00-project-map.md), [02-backend-patterns.md](../02-backend-patterns.md), [03-frontend-patterns.md](../03-frontend-patterns.md) |
| `2026-07-07-project-skeleton` | FastAPI package, config, DB init, session middleware, tests | [00-project-map.md](../00-project-map.md), [01-local-dev-and-tests.md](../01-local-dev-and-tests.md), [02-backend-patterns.md](../02-backend-patterns.md) |
| `2026-07-11-admin-ui` | Admin layout, dashboard, products, orders | [03-frontend-patterns.md](../03-frontend-patterns.md), [features/03-auth-sessions-admin.md](../features/03-auth-sessions-admin.md), [features/02-cart-checkout-orders-payments.md](../features/02-cart-checkout-orders-payments.md) |
| `2026-07-11-auth-account-frontend` | Auth context, login UI, account page, order history | [features/03-auth-sessions-admin.md](../features/03-auth-sessions-admin.md), [03-frontend-patterns.md](../03-frontend-patterns.md) |
| `2026-07-11-auth-image-upload` | Google OAuth, JWT, admin auth, image upload | [features/03-auth-sessions-admin.md](../features/03-auth-sessions-admin.md), [features/01-products-taxonomy-media.md](../features/01-products-taxonomy-media.md) |
| `2026-07-11-bilingual-i18n` | Locale routing, bilingual product/admin/UI strings | [03-frontend-patterns.md](../03-frontend-patterns.md), [features/01-products-taxonomy-media.md](../features/01-products-taxonomy-media.md), [features/05-content-contact-legal.md](../features/05-content-contact-legal.md) |
| `2026-07-11-cart-checkout` | Cart drawer/context, checkout UI, confirmation page | [features/02-cart-checkout-orders-payments.md](../features/02-cart-checkout-orders-payments.md), [03-frontend-patterns.md](../03-frontend-patterns.md) |
| `2026-07-11-engineering-excellence` | Deduplication, performance, concurrency, logging, fixtures | [features/08-performance-quality-security.md](../features/08-performance-quality-security.md), [02-backend-patterns.md](../02-backend-patterns.md), [03-frontend-patterns.md](../03-frontend-patterns.md) |
| `2026-07-11-frontend-init-design-system` | Tailwind tokens, base UI components, frontend shell | [03-frontend-patterns.md](../03-frontend-patterns.md), [01-local-dev-and-tests.md](../01-local-dev-and-tests.md) |
| `2026-07-11-orders-checkout` | Atomic checkout, order management, admin order updates | [features/02-cart-checkout-orders-payments.md](../features/02-cart-checkout-orders-payments.md), [02-backend-patterns.md](../02-backend-patterns.md) |
| `2026-07-11-product-catalog` | Product service, public/admin APIs, seed, CSV import | [features/01-products-taxonomy-media.md](../features/01-products-taxonomy-media.md), [02-backend-patterns.md](../02-backend-patterns.md) |
| `2026-07-11-product-pages` | Homepage, listing, detail, global layout | [03-frontend-patterns.md](../03-frontend-patterns.md), [features/01-products-taxonomy-media.md](../features/01-products-taxonomy-media.md) |
| `2026-07-11-product-reactions-comments` | Product comments, reactions, moderation | [features/01-products-taxonomy-media.md](../features/01-products-taxonomy-media.md), [features/08-performance-quality-security.md](../features/08-performance-quality-security.md) |
| `2026-07-11-session-cart` | Session lifecycle, cart service, quantity/stock checks | [features/03-auth-sessions-admin.md](../features/03-auth-sessions-admin.md), [features/02-cart-checkout-orders-payments.md](../features/02-cart-checkout-orders-payments.md) |
| `2026-07-11-test-performance-fixtures` | Faster pytest fixtures and helper setup | [01-local-dev-and-tests.md](../01-local-dev-and-tests.md), [features/08-performance-quality-security.md](../features/08-performance-quality-security.md) |
| `2026-07-17-admin-polish-edge-cases` | Error envelope, validation, dashboard, API docs, rate limiting | [features/08-performance-quality-security.md](../features/08-performance-quality-security.md), [02-backend-patterns.md](../02-backend-patterns.md), [features/03-auth-sessions-admin.md](../features/03-auth-sessions-admin.md) |
| `2026-07-25-email-notifications` | Email templates, order tracking, durable outbox, deliverability | [features/06-email-webhooks.md](../features/06-email-webhooks.md), [features/02-cart-checkout-orders-payments.md](../features/02-cart-checkout-orders-payments.md) |
| `2026-07-25-product-image-gallery` | Multi-image gallery, primary image, image APIs | [features/01-products-taxonomy-media.md](../features/01-products-taxonomy-media.md), [03-frontend-patterns.md](../03-frontend-patterns.md) |
| `2026-07-25-promotional-discounts` | Product discounts, effective price, checkout price snapshots | [features/01-products-taxonomy-media.md](../features/01-products-taxonomy-media.md), [features/02-cart-checkout-orders-payments.md](../features/02-cart-checkout-orders-payments.md) |
| `2026-07-25-shipping-courier-integration` | Structured delivery picker, office/city data, checkout delivery details | [features/04-shipping-delivery-couriers.md](../features/04-shipping-delivery-couriers.md), [features/02-cart-checkout-orders-payments.md](../features/02-cart-checkout-orders-payments.md) |
| `2026-07-25-social-contact-buttons` | Contact form, social links, footer | [features/05-content-contact-legal.md](../features/05-content-contact-legal.md), [03-frontend-patterns.md](../03-frontend-patterns.md) |
| `2026-07-26-dynamic-categories` | Managed taxonomy and faceted filters | [features/01-products-taxonomy-media.md](../features/01-products-taxonomy-media.md), [03-frontend-patterns.md](../03-frontend-patterns.md) |
| `2026-07-26-promotion-campaign-management` | Promotion campaigns, site banner, admin promotions | [features/01-products-taxonomy-media.md](../features/01-products-taxonomy-media.md), [03-frontend-patterns.md](../03-frontend-patterns.md) |
| `2026-07-31-add-product-video` | Product video upload/transcode/public display | [domains/02-product-media-pipeline.md](../domains/02-product-media-pipeline.md), [domains/13-product-media-editor-and-lightbox.md](../domains/13-product-media-editor-and-lightbox.md), [features/01-products-taxonomy-media.md](../features/01-products-taxonomy-media.md) |
| `2026-07-31-admin-managed-faq` | FAQ management, public FAQ, global nav/product links | [features/05-content-contact-legal.md](../features/05-content-contact-legal.md), [03-frontend-patterns.md](../03-frontend-patterns.md) |
| `2026-07-31-atelier-story-page` | About/story sections, admin editing, seed content | [features/05-content-contact-legal.md](../features/05-content-contact-legal.md), [03-frontend-patterns.md](../03-frontend-patterns.md) |
| `2026-07-31-crisp-zoom-images` | Retina images, zoom derivative, lightbox | [domains/13-product-media-editor-and-lightbox.md](../domains/13-product-media-editor-and-lightbox.md), [features/01-products-taxonomy-media.md](../features/01-products-taxonomy-media.md), [03-frontend-patterns.md](../03-frontend-patterns.md) |
| `2026-07-31-first-party-funnel-analytics` | Consent, event taxonomy, ingestion, DuckDB reports, admin analytics | [features/07-analytics-and-ml-boundary.md](../features/07-analytics-and-ml-boundary.md), [features/05-content-contact-legal.md](../features/05-content-contact-legal.md) |
| `2026-07-31-legal-compliance-foundation` | Privacy/cookies/legal links, safety metadata, checkout/email disclosures | [features/05-content-contact-legal.md](../features/05-content-contact-legal.md), [features/02-cart-checkout-orders-payments.md](../features/02-cart-checkout-orders-payments.md), [features/06-email-webhooks.md](../features/06-email-webhooks.md) |
| `2026-07-31-minimal-terms-returns-policy` | Terms page, returns/withdrawal copy, checkout disclosure | [features/05-content-contact-legal.md](../features/05-content-contact-legal.md), [03-frontend-patterns.md](../03-frontend-patterns.md) |
| `2026-07-31-product-media-editor-and-lightbox` | Image crop/rotate/quality, unified lightbox, video lightbox behavior | [domains/13-product-media-editor-and-lightbox.md](../domains/13-product-media-editor-and-lightbox.md), [domains/02-product-media-pipeline.md](../domains/02-product-media-pipeline.md), [features/01-products-taxonomy-media.md](../features/01-products-taxonomy-media.md) |
| `2026-07-31-product-mgmt-completeness` | Product admin completeness, weight, CSV/admin consistency | [features/01-products-taxonomy-media.md](../features/01-products-taxonomy-media.md), [features/04-shipping-delivery-couriers.md](../features/04-shipping-delivery-couriers.md) |
| `2026-07-31-shipping-pricing` | Live/fallback shipping cost, provenance, free shipping | [features/04-shipping-delivery-couriers.md](../features/04-shipping-delivery-couriers.md), [features/02-cart-checkout-orders-payments.md](../features/02-cart-checkout-orders-payments.md) |
| `2026-07-31-speedy-integration` | Speedy auth, waybill creation, tracking, labels | [features/04-shipping-delivery-couriers.md](../features/04-shipping-delivery-couriers.md), [features/02-cart-checkout-orders-payments.md](../features/02-cart-checkout-orders-payments.md) |
| `atelier-marie-ecommerce-mvp` | Full e-commerce MVP: products, cart/orders, admin, auth, events, recommendations | [00-project-map.md](../00-project-map.md), [features/01-products-taxonomy-media.md](../features/01-products-taxonomy-media.md), [features/02-cart-checkout-orders-payments.md](../features/02-cart-checkout-orders-payments.md), [features/07-analytics-and-ml-boundary.md](../features/07-analytics-and-ml-boundary.md) |
| `codebase-quality-sweep` | Lint cleanup, query optimization, backend/frontend dedupe | [features/08-performance-quality-security.md](../features/08-performance-quality-security.md), [02-backend-patterns.md](../02-backend-patterns.md), [03-frontend-patterns.md](../03-frontend-patterns.md) |
| `operational-hardening` | Structured logging, validation, error handling, concurrency, external resilience | [features/08-performance-quality-security.md](../features/08-performance-quality-security.md), [02-backend-patterns.md](../02-backend-patterns.md) |
| `v1-ml-first/admin-dashboard` | Historical admin dashboard and event-aware metrics | [features/03-auth-sessions-admin.md](../features/03-auth-sessions-admin.md), [features/07-analytics-and-ml-boundary.md](../features/07-analytics-and-ml-boundary.md) |
| `v1-ml-first/analytics-layer` | Historical DuckDB/materialized analytics layer | [features/07-analytics-and-ml-boundary.md](../features/07-analytics-and-ml-boundary.md) |
| `v1-ml-first/cart-management` | Historical cart/checkout persistence | [features/02-cart-checkout-orders-payments.md](../features/02-cart-checkout-orders-payments.md), [features/03-auth-sessions-admin.md](../features/03-auth-sessions-admin.md) |
| `v1-ml-first/deployment-ci` | Historical deployment, process management, backup, CI ideas | [01-local-dev-and-tests.md](../01-local-dev-and-tests.md), [features/08-performance-quality-security.md](../features/08-performance-quality-security.md) |
| `v1-ml-first/event-ingestion-pipeline` | Historical event ingestion and pipeline health | [features/07-analytics-and-ml-boundary.md](../features/07-analytics-and-ml-boundary.md) |
| `v1-ml-first/frontend-event-sdk` | Historical frontend event SDK and consent gate | [features/07-analytics-and-ml-boundary.md](../features/07-analytics-and-ml-boundary.md), [03-frontend-patterns.md](../03-frontend-patterns.md) |
| `v1-ml-first/google-oauth` | Historical OAuth/profile/JWT plan | [features/03-auth-sessions-admin.md](../features/03-auth-sessions-admin.md) |
| `v1-ml-first/maintenance-tooling` | Historical GDPR, diagnostics, optimization, disaster recovery | [features/05-content-contact-legal.md](../features/05-content-contact-legal.md), [features/08-performance-quality-security.md](../features/08-performance-quality-security.md) |
| `v1-ml-first/ml-recommendations` | Historical recommendation pipeline/cache/API | [features/07-analytics-and-ml-boundary.md](../features/07-analytics-and-ml-boundary.md) |
| `v1-ml-first/orders-checkout` | Historical order checkout and management | [features/02-cart-checkout-orders-payments.md](../features/02-cart-checkout-orders-payments.md) |
| `v1-ml-first/product-catalog` | Historical product CRUD/import/public API | [features/01-products-taxonomy-media.md](../features/01-products-taxonomy-media.md) |
| `v1-ml-first/schema-contracts` | Historical event/API/analytics contracts | [02-backend-patterns.md](../02-backend-patterns.md), [features/07-analytics-and-ml-boundary.md](../features/07-analytics-and-ml-boundary.md) |
| `v1-ml-first/session-identity` | Historical identity linking and session expiry | [features/03-auth-sessions-admin.md](../features/03-auth-sessions-admin.md), [features/07-analytics-and-ml-boundary.md](../features/07-analytics-and-ml-boundary.md) |
| `v1-ml-first/storefront-ui` | Historical storefront UI, search, layout, cart drawer | [03-frontend-patterns.md](../03-frontend-patterns.md), [features/01-products-taxonomy-media.md](../features/01-products-taxonomy-media.md), [features/02-cart-checkout-orders-payments.md](../features/02-cart-checkout-orders-payments.md) |

## Relevant Non-Archive Docs Checked

The user asked to use the archive. I did. I also checked a few current non-archive docs because current code has live systems not fully represented in the archive list.

| Non-archive source | Why it matters | Covered in |
|---|---|---|
| `openspec/changes/payment-integration` | Current code has COD/card/bank transfer and Stripe webhooks. Omitting this would mislead devs. | [features/02-cart-checkout-orders-payments.md](../features/02-cart-checkout-orders-payments.md), [features/06-email-webhooks.md](../features/06-email-webhooks.md) |
| `openspec/changes/gdpr-data-erasure` | Current/legal docs mention GDPR behavior and active erasure work. | [features/05-content-contact-legal.md](../features/05-content-contact-legal.md), [features/07-analytics-and-ml-boundary.md](../features/07-analytics-and-ml-boundary.md) |
| `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/DATABASE_SCHEMA.md` | Used to align archive summaries with current repo shape and schema. | [00-project-map.md](../00-project-map.md), [02-backend-patterns.md](../02-backend-patterns.md) |

## Known Archive Drift

- Older payment docs sometimes use names like `stripe` or `pay_on_delivery`. Current code uses `card`, `cod`, and `bank_transfer` for `payment_method`.
- Old ML-first docs assume analytics/recommendations are central. Current project treats analytics as optional and ML as deferred.
- Early product docs mention single image fields. Current product media uses gallery rows, primary image, thumbnail, zoom, and optional video.
