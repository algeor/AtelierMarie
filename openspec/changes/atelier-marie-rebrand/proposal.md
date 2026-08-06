## Why

Atelier Marie needs a storefront rebrand that feels romantic, spacious, luxurious, handmade, and trustworthy while preserving every already exposed public and admin workflow. The current UI works, but the visual direction, landing page storytelling, footer, help surfaces, and admin mobile experience need a cohesive brand system before broader polish or launch work continues.

## What Changes

- Rework the public storefront visual system around soft blush, clay, warm neutrals, sage, dark brown, and deep green-black brand tokens that are easy to customize centrally.
- Apply the note-level brand guardrails everywhere: romantic, soft, elegant, warm, handmade/boutique, and never corporate, childish, loud, or Dribbble-only at the expense of real shopping flows.
- Define a signature-style `M` brand mark direction; the main logo must not be a candle icon.
- Replace the current homepage feel with an image-led, mobile-first landing page that opens with a candle-lighting hero, slow luxury reveal motion, trust recap copy, featured products that become shoppable in the flow, and product-category entry points.
- Add landing-page product categories for available product types only, starting with Christmas balls, custom boxes, candles, and notebooks, each with delicate one-line animated drawings.
- Update category navigation so landing-page category clicks lead to the products page with the matching category/type applied and an elegant transition that never blocks navigation.
- Redesign the footer as an editorial link panel that reuses existing links, social URLs, auth/account routes, legal routes, and cookie settings without inventing missing pages.
- Update FAQ and similar help surfaces to use collapsed-by-default, popup-like in-page accordion panels with horizontally scrollable categories and optional one-by-one question reveal.
- Make admin mobile-first again, simplified, quieter, and practical, with minimal useful motion only.
- Add branded 404 and generic UI error pages that match the rebrand while keeping recovery actions obvious.
- Preserve all existing functionality, routes, states, accessibility affordances, language support, legal/support paths, checkout/account flows, and admin tools.

No breaking changes are intended.

## Capabilities

### New Capabilities

- `branded-error-pages`: Branded public 404 and generic UI error pages with recovery actions and rebrand styling.
- `storefront-page-rebrand`: Cross-page rebrand requirements for non-home public storefront pages so product detail, cart, checkout, contact, atelier/about, account/orders, legal/cookie, and auth-related pages remain visually aligned without losing functionality.

### Modified Capabilities

- `design-tokens`: Replace scattered brand color usage with central semantic tokens and customizable palette variables.
- `homepage`: Rebrand the landing page hero, trust recap, category section, product/story flow, and luxury motion behavior.
- `global-layout`: Rebrand global header/footer behavior, especially the editorial footer while preserving existing links and controls.
- `product-listing`: Support landing-page category deep links/filters and keep product browsing/filtering behavior intact.
- `faq-page`: Update FAQ presentation to collapsed-by-default accordions with horizontally scrollable category navigation.
- `admin-layout`: Make the admin shell mobile-first, simplified, visually aligned with the rebrand, and low-motion.
- `locale-ui-strings`: Ensure every new rebrand label, CTA, category name, error string, and admin/public page string is localized through the existing message files.

## Impact

- Frontend app and components under `frontend/app`, `frontend/components`, `frontend/lib`, `frontend/messages`, `frontend/app/globals.css`, and `frontend/tailwind.config.ts`.
- Static/rebrand assets under `frontend/public` and product/source media from `/Users/I551270/Desktop/untitled folder` where suitable. Photos from that folder may be used where applicable after optimization and placement in app-owned public/static assets.
- Public storefront pages: home, products, FAQ, contact, atelier/about, terms, privacy, cookies, account/order entry points, 404, and error states.
- Admin pages and admin shell: products, orders, inventory, accounting, analytics, FAQ/content, legal/privacy/cookies/terms, delivery/couriers, promotions, and payment settings.
- Tests for layout, footer, homepage, product filtering/deep links, FAQ accordion/category behavior, admin responsive behavior, error pages, accessibility, and preservation of existing exposed workflows.
