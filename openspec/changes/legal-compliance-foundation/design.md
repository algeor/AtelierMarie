## Context

Atelier Marie is a bilingual EU-facing candle store with Next.js storefront pages, FastAPI/SQLite backend, session/auth cookies, Google OAuth, contact forms, product comments, checkout, order emails, and admin product management. A completed but unarchived `minimal-terms-returns-policy` change already adds `/[locale]/terms`, returns/withdrawal content, footer Terms link, and checkout Terms disclosure.

The remaining legal foundation is broader than returns: GDPR/privacy information, cookie information, trader identity, durable order-confirmation information, product safety details for online candle offers, and cleanup of stale policy references. This change should improve launch readiness without pretending to provide country-specific legal advice.

## Goals / Non-Goals

**Goals:**

- Add public bilingual Privacy Policy and Cookie Policy pages that match current application behavior.
- Centralize trader/legal identity content so Terms, footer, emails, Privacy, Cookie, and product safety sections do not drift.
- Extend existing Terms content rather than creating a separate Returns page.
- Add product safety metadata for candles and render it on product pages.
- Add customer-facing legal/privacy notices at data submission and order-confirmation surfaces.
- Fix stale FAQ wording and sitemap coverage.
- Keep implementation compatible with existing i18n, SQLite migrations, and OpenSpec changes.

**Non-Goals:**

- No cookie consent banner until non-essential analytics/ads/tracking scripts are introduced.
- No returns portal, refund automation, or admin return workflow.
- No courier API shipping-price calculation; that remains in `shipping-pricing`.
- No executable GDPR erasure/retention backend; that remains in `gdpr-data-erasure`.
- No legal finalization of real trader values; the owner must provide and review the legal name, address, registration/VAT status, and target-country assumptions.

## Decisions

### 1. Keep legal policy content static and localized

Use static localized message content and server-rendered routes for `/[locale]/privacy` and `/[locale]/cookies`, matching the existing `/[locale]/terms` approach.

Rationale: legal policy text should change deliberately through review and deployment. Admin-managed legal copy is unnecessary for launch and increases the chance of accidental policy drift.

Alternative considered: admin-editable policies. Rejected for MVP because it adds persistence, auditing, preview, and permission concerns without solving a current operational need.

### 2. Centralize trader identity in one frontend source

Create a small legal identity source for storefront rendering, for example `frontend/lib/legal.ts` plus localized labels/messages. It should include the public values needed across legal pages and emails: trading name, legal name, country, geographic address, contact email, registration number, VAT status/number if applicable, and policy URLs.

Rationale: the current Terms copy says only that Atelier Marie is based in Bulgaria. Repeating real identity values manually across several JSON sections and email templates would make drift likely.

Alternative considered: environment variables for legal identity. Rejected unless deployment-specific identity is actually needed; these are public legal facts and should be reviewable in source.

### 3. Privacy and cookie pages document current behavior only

Privacy Policy should cover current data processing categories: sessions, cart, orders, delivery details, contact messages, comments/reactions, Google OAuth profile data, Stripe/payment references, transactional email delivery, suppression lists, logs, and admin operations. Cookie Policy should list current cookies: backend session cookie, auth cookie, locale cookie, and any framework-required cookies if observed.

Rationale: policy text must match actual behavior. The code search found no analytics, ads, Meta/Google tracking, Hotjar, PostHog, newsletter marketing, or similar non-essential tracking.

Alternative considered: adding a generic consent management banner now. Rejected because it would imply non-essential tracking exists and add UX complexity before there is anything meaningful to consent to.

### 4. Product safety uses global responsible-party info plus per-product warnings

For handmade candles sold by Atelier Marie, manufacturer/trader and EU responsible person can default to the same centralized legal identity. Product-specific fields should capture safety/care content that can vary by candle:

- `safety_warnings_en`, `safety_warnings_bg`
- `care_instructions_en`, `care_instructions_bg`
- optional `safety_notes_en`, `safety_notes_bg` if a product needs extra listing-specific warnings

The public product identifier should remain the existing product `id`; no new SKU system is needed for this change.

Rationale: GPSR online offers need product identification and safety/manufacturer/responsible-party information. Most identity information is global for this store, while warnings/care can vary by product.

Alternative considered: storing manufacturer/responsible-party fields per product. Rejected for MVP because it duplicates the same public data on every handmade candle. It can be revisited if the store sells third-party products.

### 5. Extend product API/admin surfaces conservatively

Add safety/care fields to product schema, admin create/update models, admin product response, CSV import, public product response, mock API, and product form. Render the safety section only when content exists, but always show global responsible-party/trader information on product detail pages once legal identity is configured.

Rationale: admin users need a controlled way to enter warnings, product pages need to show them, and tests should cover the API round trip.

Alternative considered: hardcoded safety text only in FAQ. Rejected because product offers need the relevant information close to the product, and some candles may require product-specific notes.

### 6. Checkout/order surfaces should not duplicate shipping-pricing

This change should fix legal clarity without building courier-price calculation. Checkout should display the charged item prices using `effective_price_cents`, show the known shipping value when available, and avoid suggesting a total includes paid delivery if it does not. Order confirmation pages should show item subtotal, shipping, and total from `OrderResponse` fields.

Rationale: `shipping-pricing` already owns courier calculation and server validation. This change should not create a competing half-implementation.

Alternative considered: implementing a flat shipping fee here. Rejected because it conflicts with the existing `shipping-pricing` proposal and could create compliance risk if real courier costs differ.

### 7. Durable order information goes into emails as links and concise text

Transactional order emails should include concise policy/trader references and stable links to Terms, Privacy, and Cookie pages. They should not attempt to paste the full legal documents into every email.

Rationale: emails are the durable customer-facing channel already implemented. Links plus key withdrawal/trader/contact text are practical and keep templates readable.

Alternative considered: PDF attachment generation. Rejected for MVP because it adds document generation, storage, and attachment-delivery risk.

### 8. FAQ seed needs an idempotent content update

The seeded FAQ currently references a non-existent standalone Returns & Refunds Policy. Update seed text and add a marker-guarded migration that only rewrites the known old default answer to point to Terms & Conditions.

Rationale: FAQ is admin-managed, so changing the seed alone does not fix existing databases. A conservative migration avoids overwriting owner-edited FAQ content.

## Risks / Trade-offs

- **Legal text may still be incomplete for a specific Member State** -> Keep copy as a baseline and flag owner/lawyer review before launch.
- **Real trader identity is unknown during implementation** -> Use explicit placeholders or a single legal identity source that fails visibly in development until filled, rather than burying fake data.
- **GPSR interpretation can vary by product** -> Provide product-specific safety fields and keep global responsible-party information easy to change.
- **Cookie consent may become necessary later** -> Cookie Policy should state current no-analytics behavior; add a separate consent-management change when non-essential tracking is introduced.
- **Shipping remains incomplete if paid delivery is used at launch** -> Do not hide the gap; either finish `shipping-pricing` or ensure checkout explicitly states delivery charges are zero/included/manual before accepting orders.
- **Email links depend on public site URL configuration** -> Use `NEXT_PUBLIC_SITE_URL`/frontend URL patterns consistently and test generated template context.
- **FAQ migration could overwrite owner changes** -> Only update rows matching the exact old seeded text and guard it with a schema migration marker.

## Migration Plan

1. Add new product safety columns with defaults allowing existing products to keep working.
2. Update service/model/admin/public API mappings and mock API in the same change so TypeScript and Pydantic stay aligned.
3. Add legal policy routes and messages after centralizing legal identity.
4. Update footer, contact form, checkout, order confirmation, product detail, and email templates.
5. Add the conservative FAQ text migration marker.
6. Run backend model/admin/product tests and focused frontend policy/checkout/product tests.

Rollback is straightforward for frontend-only policy/disclosure changes. Product safety DB columns can remain unused if the UI is rolled back; they should be additive and nullable/defaulted so existing data is not damaged.

## Open Questions

- What exact legal name, geographic address, registration number, VAT status, and responsible-person details should be displayed?
- Are prices VAT-inclusive, VAT-exempt, or outside VAT registration? The wording must match the real tax status.
- Will the first launch charge delivery inside checkout, treat delivery as free, or collect delivery separately through the courier? This determines the exact checkout wording until `shipping-pricing` lands.
- Does the owner want Privacy/Cookie pages as separate footer links, or a single Privacy page with a cookie section plus a direct `#cookies` anchor?
- Should safety warnings be seeded with a default candle warning template for all existing products, or require admin review per product before launch?
