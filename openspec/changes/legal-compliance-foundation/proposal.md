## Why

Atelier Marie now has a Terms & Conditions page with withdrawal/returns text, but the storefront still lacks the broader EU/Bulgaria legal foundation needed before launch. The site processes personal data, uses cookies, sells physical candles, accepts orders, sends transactional emails, and displays product comments, so compliance needs to cover policy pages, pre-purchase disclosures, post-purchase confirmations, and product safety information.

## What Changes

- Add localized Privacy Policy and Cookie Policy pages covering the data/cookie behavior actually present in the app: session/auth/locale cookies, orders, delivery data, contact messages, comments, Google OAuth, Stripe payment references, and transactional email delivery.
- Expand the existing Terms & Conditions content with full trader identity placeholders/fields, legal contact details, stronger price/tax/payment wording, and clear links from related surfaces.
- Add footer discoverability for Privacy Policy and Cookie Policy while keeping returns inside Terms & Conditions rather than introducing a standalone Returns page.
- Add small privacy/legal notices near the contact form and checkout order submission, linking to the relevant policies.
- Update order confirmation UI and transactional order emails to reference Terms & Conditions, withdrawal/returns information, trader contact details, and policy links in a durable customer-facing channel.
- Add GPSR-oriented product safety metadata for candle listings: product identifier, manufacturer/trader or responsible-person details, safety warnings/care information, and a storefront rendering section.
- Fix stale FAQ wording that references a non-existent standalone Returns & Refunds Policy, pointing customers to Terms & Conditions instead.
- Include legal policy routes in sitemap/metadata and add focused frontend/backend tests for the new policy and product-safety behavior.
- Non-goals: cookie consent banner for analytics/ads, returns portal, refund automation, jurisdiction-specific legal advice, courier API shipping calculation, and the executable GDPR erasure backend already tracked by `gdpr-data-erasure`.

## Capabilities

### New Capabilities
- `privacy-cookie-policy`: Public localized Privacy Policy and Cookie Policy pages, including cookie inventory and GDPR/ePrivacy-facing explanations for current site behavior.
- `product-safety-compliance`: Product-safety metadata capture and storefront presentation for physical candle offers.

### Modified Capabilities
- `global-layout`: Footer exposes required legal policy links and quiet trader/contact discoverability.
- `checkout-ui`: Checkout displays policy/privacy disclosure and avoids misleading totals before order submission.
- `contact-form`: Contact form displays a privacy notice and links to Privacy Policy before personal-data submission.
- `order-confirmation-ui`: Order confirmation surfaces policy links and total/shipping breakdown needed after purchase.
- `email-templates`: Transactional order emails include durable references to Terms, withdrawal/returns, trader contact, and policy links.
- `product-admin-api`: Admin product create/update/read surfaces product-safety metadata fields.
- `product-public-api`: Public product responses expose product-safety metadata needed for online offers.
- `product-detail`: Product detail pages render product-safety, warning, and responsible-party information.

## Impact

- **Frontend:** new localized policy pages, footer links, checkout/contact/order disclosure copy, product detail safety section, sitemap updates, i18n messages, and focused Vitest coverage.
- **Backend:** product schema/model/service/admin route updates for safety metadata, public product response updates, seed/migration defaults where appropriate, and backend tests.
- **Email:** order confirmation/payment-pending templates in both locales gain policy and trader/contact references.
- **OpenSpec coordination:** depends conceptually on `minimal-terms-returns-policy`; avoids duplicating `gdpr-data-erasure` and `shipping-pricing` implementation work.
- **Compliance:** improves operational readiness but remains a compliance implementation baseline, not legal advice; final legal text still needs owner/lawyer review with the real trader identity and target countries.
