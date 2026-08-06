## Context

The frontend is a localized Next.js storefront with a FastAPI backend and existing public/admin features. The current UI already exposes product browsing, product detail pages, cart, checkout, delivery, payments, auth/account, orders, contact, FAQ, legal/cookie pages, social links, and a broad admin panel. The rebrand notes in `docs/atelier-marie-ui-notes.md` define the target mood: romantic, soft, elegant, warm, handmade/boutique, mobile-first, and function-preserving.

The most important constraint is preservation: the rebrand MUST NOT remove, hide, or break existing exposed functionality. Design changes can relocate or restyle features only when they remain discoverable, accessible, and tested.

## Goals / Non-Goals

**Goals:**

- Establish a central, easy-to-customize brand token system for the rebrand palette and semantic UI colors.
- Make the visual direction traceable to the UI notes: romantic, soft, elegant, warm, handmade/boutique, and explicitly not corporate, childish, loud, card-heavy, or merely decorative.
- Establish a logo/brand-mark direction around a handmade signature-style `M`, not a candle icon.
- Rework the homepage into a product-led, mobile-first landing page with hero media first, a scrollable story/trust flow, category entry points, featured products that become shoppable in the flow, and slow luxury motion.
- Add delicate one-line category drawings and category-to-products navigation for categories with at least one product.
- Redesign the footer as an editorial link panel that reuses existing routes and controls.
- Make FAQ/help pages easier to scan with collapsed-by-default accordions and horizontal category navigation.
- Make the admin panel mobile-first, simplified, quieter, and low-motion while preserving all admin tools.
- Add branded 404 and generic UI error pages.
- Align remaining public pages with the rebrand without reducing their purpose: product detail, cart, checkout, contact, atelier/about, account/orders, terms, privacy, cookies, and auth-related recovery pages.
- Localize every new rebrand string in both supported locales.
- Validate responsiveness, accessibility, reduced-motion behavior, and existing workflow preservation.

**Non-Goals:**

- No backend data model changes unless product category/type data is missing and cannot be derived from existing fields.
- No checkout/payment flow redesign beyond visual token alignment and preservation testing.
- No fake newsletter subscription flow. Footer can reserve that space only if no real consent-aware subscription exists.
- No removal of product comments, reactions, safety details, delivery/courier flows, account/order flows, legal/support pages, or admin modules.
- No heavy decorative motion in admin, checkout, payment, forms, or legal-heavy pages.

## Decisions

### Decision: Use semantic CSS variables backed by Tailwind tokens

Use one central color source for brand values and expose semantic variables such as `--color-page`, `--color-surface`, `--color-text`, `--color-muted`, `--color-border`, `--color-primary`, `--color-accent`, `--color-danger`, `--color-success`, and admin-specific quiet variants. Tailwind brand classes can map to these variables, but components should prefer semantic tokens over one-off hex values.

Alternatives considered:
- Continue adding named Tailwind colors directly in components: faster initially, but hard to customize and easy to drift.
- Inline CSS colors per component: rejected because it makes palette swaps and contrast audits expensive.

### Decision: Use a signature-style `M` as the brand mark

The main logo/brand mark should be a beautiful, handmade signature letter `M` that pairs with the readable `Atelier Marie` wordmark. Candle drawings are appropriate for category/product decoration only, not as the main brand identity. The `M` may animate with a one-time signature draw effect in high-emphasis moments and must have a static fallback for reduced motion and small placements.

Alternatives considered:
- Candle logo: rejected by brand direction; it is too literal and should not be used as the main mark.
- Text-only wordmark everywhere: acceptable as fallback, but less distinctive than a signature `M` paired with the wordmark.

### Decision: Treat the homepage as a composed landing sequence, not a marketing splash

The homepage should render as a mobile-first vertical sequence: hero media first, category entry points, trust recap/about-story bridge, featured products that can become shoppable in the same flow, and editorial footer. Existing featured-product behavior remains; it can move in the sequence but not disappear. The first viewport should immediately signal Atelier Marie through product or atelier lifestyle media, not a generic marketing block.

Alternatives considered:
- Keep only the current hero + featured grid: too limited for the desired rebrand.
- Build a landing page disconnected from real products: rejected because categories must appear only when products exist.

### Decision: Derive landing categories from product data

The category section should display only categories/types that have at least one product. Initial expected labels are Christmas balls, custom boxes, candles, and notebooks, but the implementation should derive availability from existing product category/type metadata and use a small mapping for artwork/labels.

Alternatives considered:
- Hardcode all categories: rejected because empty categories would lead to dead-end UX.
- Add new static category content management first: deferred unless existing product metadata cannot support the requirement.

### Decision: Use inline SVG/vector drawings for category line art

Use small SVG assets/components for one-line category drawings. Animate with stroke-dash drawing and transform/opacity only, with a static fallback for reduced motion. Store reusable assets under `frontend/public/rebrand` or as typed React components if they need theme-aware color.

Alternatives considered:
- Raster illustrations: less crisp and harder to recolor.
- Icon library icons: faster but too generic for the handmade brand feel.

### Decision: Keep luxury motion restrained and optional

Use slow reveal, gentle parallax, product image settling, line drawing, soft panel expansion, and footer wordmark reveal where they support comprehension. Use `prefers-reduced-motion` fallbacks globally. Avoid motion in checkout, payment, admin workflows, legal-heavy pages, and critical forms.

Alternatives considered:
- Broad page-transition framework: likely overkill and risky for route reliability.
- Heavy scroll pinning: rejected because the site must remain natural on mobile.

### Decision: Use in-page staged FAQ reveals, not modal popups

FAQ questions can reveal one by one as soft popup-like panels when a category loads or changes, but the answers remain collapsed by default and stay in the page flow. The category strip remains horizontally scrollable on mobile, active state remains clear, and reduced-motion users receive the same collapsed content without decorative stagger.

Alternatives considered:
- Blocking modal popups for answers: rejected because they trap focus and make mobile scanning harder.
- Showing every answer by default: rejected because the user asked for collapsed questions and category-based scanning.

### Decision: Rebrand critical workflow pages with tokens, not decorative rebuilds

Product detail, cart, checkout, account/orders, contact, and legal pages should receive token, spacing, typography, and responsive polish while preserving their current information architecture. Checkout and payment surfaces should stay functional and low-motion.

Alternatives considered:
- Apply the same editorial homepage treatment everywhere: rejected because critical workflows need speed, clarity, and predictable controls.
- Leave non-home pages visually unchanged: rejected because the user asked for a whole-site rebrand.

### Decision: Treat all new rebrand text as localized UI copy

All new hero text, trust recap copy, category labels, footer group headings, error-page copy, and admin labels should live in the existing `messages/en.json` and `messages/bg.json` files.

Alternatives considered:
- Hardcode English strings during the visual pass: rejected because localization is already a site contract and hardcoded copy would regress Bulgarian support.

### Decision: Optimize selected source photos into app-owned public assets

Photos from `/Users/I551270/Desktop/untitled folder` may be used where applicable for hero, category, trust, footer, and other rebrand surfaces when they improve the page. The implemented site should reference optimized assets under the frontend public/static tree, not the desktop source folder. If moving flame media is created, provide a still fallback and reduced-motion behavior.

Alternatives considered:
- Reference the desktop source folder directly: rejected because it will not work in deployed or shared environments.
- Require video hero before launch: deferred; a still image fallback is enough if video/cinemagraph quality is not ready.

### Decision: Redesign footer by regrouping existing links only

Footer columns should group Explore, Help, My Account, Legal, and Social using current routes and controls. Do not add reference-only pages like delivery, returns, appointment, find a store, sustainability, or giving back unless those features already exist.

Alternatives considered:
- Copy the reference footer link set: rejected because it would expose nonexistent routes.
- Keep one flat footer row: preserves functionality but misses the requested editorial finish.

### Decision: Make admin mobile-first without storefront theatrics

Admin should share the rebrand palette but use quieter tokens, compact spacing, single-column forms on mobile, mobile-friendly list/card table alternatives, reachable filters/actions, and minimal motion for drawer/open/save/loading only.

Alternatives considered:
- Apply storefront editorial layout to admin: rejected because admin is a repeated-use work surface.
- Desktop-first admin cleanup only: rejected because the user explicitly wants mobile-first again.

## Risks / Trade-offs

- Existing feature regression -> Mitigate with a route/workflow preservation audit before implementation and regression tests after each major visual pass.
- Product category metadata mismatch -> Mitigate by inspecting current product taxonomy/category fields before implementing landing categories; add mapping only after confirming source data.
- Motion causing poor mobile performance or accessibility issues -> Mitigate with transform/opacity animations, reduced-motion support, and Playwright checks on mobile/desktop.
- Text over hero media loses contrast -> Mitigate with deliberate free-space image selection, responsive overlays only where needed, and contrast checks.
- Visual direction becomes a copied Dribbble concept or hides shopping actions -> Mitigate with a notes-to-spec coverage audit, real product data, existing route reuse, and explicit preservation tests.
- Signature `M` becomes illegible at small sizes -> Mitigate with small-size testing, simplified static variant, and text wordmark fallback.
- Admin simplification hides advanced controls -> Mitigate by grouping/collapsing advanced tools rather than removing them.
- Legal/help accordions hide required information too deeply -> Mitigate by applying accordion patterns only where legally appropriate and keeping critical legal text visible or easy to expand.
- Palette customization creates inconsistent states -> Mitigate with semantic token documentation and tests/visual QA for hover, focus, disabled, success, warning, error, and contrast.
- Hardcoded or English-only rebrand copy -> Mitigate by adding localized message-file requirements and tests for both locales.
- Local desktop media path leaks into production code -> Mitigate by processing selected media into frontend public/static assets and testing built asset paths.

## Migration Plan

1. Audit current public/admin routes, components, tests, and exposed workflows.
2. Introduce semantic color tokens and map current UI to tokens without layout changes.
3. Rebrand global shell/footer and verify existing links, social URLs, language, auth, cart, cookie settings, and legal routes.
4. Rebuild homepage sections incrementally behind existing data sources.
5. Add category line assets and product-derived landing category navigation.
6. Update FAQ/help interaction patterns.
7. Rebrand remaining public page families with token/spacing/layout polish while preserving workflows.
8. Update admin layout and shared admin surfaces mobile-first.
9. Add branded 404/error pages.
10. Localize all new rebrand strings.
11. Compare the implemented surfaces against `docs/atelier-marie-ui-notes.md` so the final pass covers notes that are easy to miss, including footer link grouping, FAQ staged reveal, category transition behavior, visual mood guardrails, and reduced-motion fallbacks.
12. Run unit/component tests, build checks, and Playwright visual/interaction checks across mobile and desktop.

Rollback strategy: keep changes scoped by component and route. If a visual pass breaks a workflow, revert the affected component-level change while retaining token groundwork where safe.

## Open Questions

- Which product field should be the canonical source for landing categories: current category, taxonomy type, labels, or a new explicit product type?
- Is there a real newsletter subscription/consent flow planned, or should footer newsletter space remain social/contact-focused for now?
- Which exact hero media asset from `/Users/I551270/Desktop/untitled folder` should be used, and does a moving-flame loop need to be created from still imagery?
- Should FAQ allow one open question per category/section, or multiple open questions at once? Existing behavior allows one open per section.
