# Atelier Marie Rebrand Preservation Audit

Created: 2026-08-02
Change: `atelier-marie-rebrand`

## Rule

The rebrand must not remove, hide, or break exposed functionality. If a feature moves, it must remain findable, usable, localized, accessible, and covered by verification.

## Route Inventory

Current localized route files found: 50.

### Public Storefront

- Home: `/[locale]`
- Products: `/[locale]/products`, `/[locale]/products/[id]`
- Product states: product loading, product not found, products error/loading
- Cart: global cart drawer from header/cart context
- Checkout: `/[locale]/checkout`
- Account/orders: `/[locale]/account`, `/[locale]/orders`, `/[locale]/orders/[id]`, `/[locale]/orders/[id]/confirmation`, `/[locale]/orders/[id]/retry-payment`
- Support/content: `/[locale]/contact`, `/[locale]/faq`, `/[locale]/atelier`
- Legal/privacy: `/[locale]/terms`, `/[locale]/privacy`, `/[locale]/cookies`
- Auth callback: `/[locale]/auth/callback`
- Global localized layout/loading: `/[locale]/layout`, `/[locale]/loading`

### Admin

- Admin shell/dashboard: `/[locale]/admin`
- Products: `/[locale]/admin/products`, `/[locale]/admin/products/new`
- Orders: `/[locale]/admin/orders`, `/[locale]/admin/orders/[id]`
- Delivery/couriers: `/[locale]/admin/delivery`, `/[locale]/admin/delivery/econt`, `/[locale]/admin/delivery/speedy`, `/[locale]/admin/econt`, `/[locale]/admin/speedy`
- Content/legal: `/[locale]/admin/atelier`, `/[locale]/admin/faq`, `/[locale]/admin/legal`, `/[locale]/admin/privacy`, `/[locale]/admin/cookies`, `/[locale]/admin/terms`
- Inventory/accounting: `/[locale]/admin/inventory`, materials, movements, batches, recipes, valuation, `/[locale]/admin/accounting`
- Business tools: `/[locale]/admin/analytics`, `/[locale]/admin/promotions`, `/[locale]/admin/settings/payments`, `/[locale]/admin/taxonomy`

## Preservation Map

- Global shell -> header navigation, language toggle, auth/account, cart, announcement, cookie settings, footer links/social/legal.
- Homepage -> hero, featured products, product links, category entry points, trust recap, loading/empty states.
- Products listing -> category filters, search/sort where present, cards, images/placeholders, prices/discounts, empty/loading/error states.
- Product detail -> gallery, thumbnails, media fallback, product information, stock states, quantity selector, add-to-cart, FAQ links, safety/responsible-party info, comments/reactions.
- Cart -> drawer open/close, focus trap, item quantities, remove, subtotal, empty state, checkout link, optimistic/error states, badge.
- Checkout -> contact fields, delivery/courier flow, office/address selection, shipping price, payment method, legal/privacy disclosure, validation, submit/loading/error.
- Account/orders -> auth prompt, profile, order list/detail, confirmation, retry payment, status timeline, empty/loading/error states.
- Support/content -> contact form, FAQ, atelier managed sections, localized content, structured data where present.
- Legal/privacy -> full policy content, section navigation, anchors, cookie inventory, trader/contact discoverability.
- Admin -> every module route/action/settings path listed above; simplify by grouping, not removing.

## Existing Test Protection

Current frontend test files found: 69.

Key existing coverage includes:

- Layout: `Header.test.tsx`, `Footer.test.tsx`, `LanguageToggle.test.tsx`, `LocaleChrome.test.tsx`, announcement bar tests.
- Products: product listing client, product gallery, product detail app tests, price display, add-to-cart, cart drawer.
- Checkout/delivery: checkout app tests and delivery section tests.
- FAQ/contact/legal: FAQ app/component tests, contact form tests, terms/legal page tests.
- Account/orders/auth: account and orders page tests, order detail/confirmation/retry-payment tests, login/user menu tests, auth callback tests.
- Admin: dashboard, products, orders, payment settings, analytics, delivery, inventory, legal/privacy, econt/speedy, promotions, FAQ/content manager tests.
- Context/lib: cart, auth, cookie consent, API locale, analytics, middleware locale, media, validation.

## Baseline Screenshots

Captured with local Next dev server on `http://127.0.0.1:3001` using `NEXT_PUBLIC_USE_MOCK_API=true`.

Output folder: `qa-artifacts/screenshots/2026-08-02/rebrand-baseline/`

Captured pages:

- Home: `home-390.png`, `home-1440.png`
- Products: `products-390.png`, `products-1440.png`
- Product detail: `pdp-390.png`, `pdp-1440.png`
- Cart empty drawer: `cart-empty-open-390.png`
- Checkout empty-cart redirect behavior: `checkout-empty-redirect-390.png`, `checkout-empty-redirect-1440.png`
- FAQ: `faq-390.png`, `faq-1440.png`
- Contact: `contact-390.png`, `contact-1440.png`
- Atelier: `atelier-390.png`, `atelier-1440.png`
- Terms/privacy/cookies: mobile and desktop captures for each
- Account/orders: mobile and desktop captures for each
- Admin dashboard/products: mobile and desktop captures for each

Existing prior QA screenshots remain useful for richer cart/checkout/admin states, especially `qa-artifacts/screenshots/2026-07-31/`.

## Rebrand QA Checklist

## Public Mood Guardrail Review

Reviewed on 2026-08-02 during implementation of `atelier-marie-rebrand`.

- Homepage uses an image-led hero, signature `M`, soft reveal motion, trust recap, real product/category data, and clear shop/product actions.
- Product detail, cart, checkout, contact, account/orders, and legal pages use semantic rebrand tokens while keeping practical typography, prices, forms, disclosures, and recovery actions visible.
- FAQ uses in-page collapsed panels and a horizontal category strip rather than blocking modals.
- Footer is a composed editorial panel with existing route groups only; it does not add unavailable reference links or a fake newsletter form.
- Legal pages keep policy text, anchors, policy cross-links, cookie inventory, and trader/contact information visible without decorative hiding.
- Brand placement uses the signature-style `M` or accessible `Atelier Marie` text; candle drawings remain decorative/category/error artwork only.
- Admin and checkout remain low-motion work surfaces; storefront decorative motion is limited to reveal, line drawing, soft panel expansion, and footer wordmark behavior with reduced-motion fallbacks.

Result: public rebrand surfaces align with the romantic, soft, elegant, glassy, handmade/boutique guardrails without making commerce, support, account, checkout, or legal tasks harder to find.

- [x] No existing route listed in this audit disappears.
- [x] Header controls remain visible/reachable on mobile and desktop.
- [x] Footer includes only existing links/routes and no fake reference-only pages.
- [x] Language toggle and all new rebrand strings work in EN and BG.
- [x] Product listing filters/deep links work and invalid filters fall back safely.
- [x] Product detail still exposes gallery, price/discount, safety, FAQ links, comments/reactions, and add-to-cart.
- [x] Cart drawer still traps focus, closes correctly, updates quantities, removes items, and links checkout.
- [x] Checkout keeps all delivery/payment/legal/validation behavior and avoids decorative blocking motion.
- [x] FAQ questions are collapsed by default, categories scroll horizontally, and keyboard/ARIA behavior works.
- [x] Admin modules remain reachable; advanced controls are grouped, not removed.
- [x] Legal pages remain complete and readable; critical legal text is not hidden too deeply.
- [x] Signature `M` is the brand mark if available; candle drawings are never used as the main logo.
- [x] Decorative motion respects reduced-motion preferences.
- [x] Focus states and contrast remain readable after palette changes.
- [x] Final Playwright/CDP screenshots cover mobile and desktop before completion.

Final walkthrough evidence:

- Focused preservation tests passed for header/footer, homepage categories, product deep links, FAQ, contact, legal, account/orders, cart, checkout, branded errors, and admin products.
- Full frontend test suite passed: 73 files, 390 tests.
- Frontend typecheck passed.
- Frontend lint exited successfully with existing warnings.
- Playwright Chrome sweep passed on 390px mobile and 1440px desktop for home, products, product detail, cart drawer, checkout, FAQ, contact, atelier, account, orders, terms, privacy, cookies, branded 404/product not-found, footer, admin dashboard, and admin products.
- Reduced-motion Chrome sweep passed for homepage reveal/signature/footer motion, products, cart/checkout, FAQ accordion, and admin transition behavior.
- Hardcoded-color scan on touched frontend files has only tokenized `rgb(var(--color-...))` uses remaining.
