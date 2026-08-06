## 1. Baseline And Preservation Audit

- [x] 1.1 Inventory all existing localized public routes, admin routes, global controls, footer links, auth/account/order flows, cart/checkout flows, legal/support pages, and exposed UI states.
- [x] 1.2 Map each existing exposed feature to the rebrand surface where it will remain available.
- [x] 1.3 Capture current mobile and desktop screenshots for homepage, products, product detail, cart, checkout, FAQ, contact, atelier, legal pages, account/orders, and core admin pages.
- [x] 1.4 Identify current frontend tests that protect footer, header, product listing, FAQ, admin layout, cart/checkout, and legal routes.
- [x] 1.5 Add or update a rebrand QA checklist that explicitly verifies no exposed functionality disappeared.

## 2. Token System And Brand Foundation

- [x] 2.1 Define central rebrand palette tokens and semantic CSS variables for page, surface, text, muted text, border, primary action, secondary action, accent, focus, success, warning, and error.
- [x] 2.2 Map Tailwind color utilities to the central token layer without breaking existing class names that are still used.
- [x] 2.3 Add quieter admin semantic token choices that reuse the same palette foundation.
- [x] 2.4 Replace hardcoded rebrand-related color values in touched components with semantic tokens.
- [x] 2.5 Document token names and palette customization rules near the token definitions.
- [x] 2.6 Verify text, focus, hover, disabled, success, warning, and error contrast on the default palette.

## 3. Rebrand Assets And Motion Foundation

- [x] 3.1 Review product source media in `/Users/I551270/Desktop/untitled folder` and select candidate photos for hero, category, trust, footer, and other applicable rebrand surfaces.
- [x] 3.2 Prepare the landing hero media direction: gentle hand lighting candle, natural short manicure, visible candle/product, and free text/logo space.
- [x] 3.3 Create or refine the primary signature-style `M` brand mark and confirm it is not a candle logo.
- [x] 3.4 Create a static small-size variant and optional subtle signature-draw animation for the `M` mark.
- [x] 3.5 Create or refine one-line SVG drawings for candles, Christmas balls, custom boxes, and notebooks as category/product decoration only.
- [x] 3.6 Add reusable motion utilities for slow reveal, line drawing, soft panel expansion, signature draw, and footer wordmark reveal.
- [x] 3.7 Add reduced-motion fallbacks for all decorative animation utilities.
- [x] 3.8 Verify animated assets have stable dimensions and do not shift layout on mobile or desktop.

## 4. Homepage Rebrand

- [x] 4.1 Rebuild the homepage hero as an image-led mobile-first section with brand name/logo space, short supporting copy, and products CTA.
- [x] 4.2 Preserve homepage featured product fetching, featured product rendering, product detail links, loading state, and empty-featured behavior.
- [x] 4.3 Add the landing-page trust recap section with handmade, premium organic wax blend, high-quality fragrance, finish, gift-ready, and support signals.
- [x] 4.4 Derive available landing categories from real product category/type data and hide categories with no products.
- [x] 4.5 Render landing category entries for Christmas balls, custom boxes, candles, and notebooks when matching products exist.
- [x] 4.6 Wire each homepage category entry to the products page with the category/type encoded in the URL.
- [x] 4.7 Add restrained homepage motion for hero reveal, category line drawings, trust recap reveal, product card settling, and footer approach.
- [x] 4.8 Verify the homepage remains vertically natural on mobile and avoids scroll traps or hover-only interactions.
- [x] 4.9 Shape the landing sequence as hero media first, story/trust reveal, featured shoppable product flow, product categories, and editorial footer.
- [x] 4.10 Add category-to-products transition polish that feels editorial but keeps route changes, keyboard activation, and browser navigation immediate.

## 5. Products Page Deep Links And Card Polish

- [x] 5.1 Teach the products page to read a supported category/type query parameter and initialize the selected filter.
- [x] 5.2 Keep invalid category/type query parameters safe by falling back to the `All` view.
- [x] 5.3 Preserve existing product filtering, sorting/search where present, product cards, images/placeholders, pricing/discount display, empty state, loading state, and error state.
- [x] 5.4 Add subtle product-card hover/focus motion that does not resize the grid or hide product information.
- [x] 5.5 Verify category filter updates remain keyboard accessible and announced to screen readers.

## 6. Global Layout And Editorial Footer

- [x] 6.1 Redesign the footer as an editorial translucent panel with grouped Explore, Help, My Account, Legal, and Social sections.
- [x] 6.2 Reuse only existing routes and controls: Home, Shop, Atelier, FAQ, Contact, Sign in/Login, My Account, My Orders, Terms, Privacy, Cookies, cookie settings, Instagram, and TikTok.
- [x] 6.3 Ensure the footer does not add unavailable reference-only links such as Order Tracking, Delivery, Return, Appointment, Find a Store, Sustainability, or Giving Back.
- [x] 6.4 Add the large decorative `ATELIER MARIE` footer wordmark with a non-blocking mobile/desktop layout.
- [x] 6.5 Preserve header navigation, language toggle, auth/account control, cart control, announcement behavior, and cookie consent/settings behavior.
- [x] 6.6 Verify footer links, social URLs, legal links, account links, and cookie settings in localized routes.

## 7. FAQ And Help Surfaces

- [x] 7.1 Update FAQ questions to render collapsed by default.
- [x] 7.2 Keep accordion buttons semantic with `aria-expanded`, `aria-controls`, keyboard activation, visible focus, and reduced-motion support.
- [x] 7.3 Add horizontally scrollable FAQ category navigation with clear active category state.
- [x] 7.4 Ensure selecting a FAQ category shows the relevant collapsed questions and keeps section anchors usable.
- [x] 7.5 Style expanded answers as soft in-page panels rather than blocking modals.
- [x] 7.6 Identify other help/legal surfaces that can safely reuse the pattern without hiding required legal text too deeply.
- [x] 7.7 Add optional one-by-one FAQ question reveal on page load/category switch with all answers still collapsed and reduced-motion fallback.

## 8. Admin Mobile-First Simplification

- [x] 8.1 Audit existing admin modules and actions to confirm every route/tool remains reachable after simplification.
- [x] 8.2 Rework admin shell navigation for mobile-first use while preserving desktop sidebar behavior and active states.
- [x] 8.3 Convert mobile admin forms to readable single-column flows with clear labels, errors, and save actions.
- [x] 8.4 Convert dense mobile admin tables into readable lists/cards or responsive alternatives without removing fields/actions.
- [x] 8.5 Group advanced admin controls into clear sections, tabs, drawers, or collapsible groups instead of removing them.
- [x] 8.6 Apply quieter admin semantic tokens and remove storefront-style decorative layouts from admin pages.
- [x] 8.7 Limit admin motion to focus/hover, drawer open/close, loading, and save confirmation feedback.

## 9. Branded Error Pages

- [x] 9.1 Add a localized branded 404 page with oversized `404`, `Not Found`, short recovery copy, and `Back to Home` action.
- [x] 9.2 Add a localized generic frontend error page with `Something went wrong.`, safe recovery copy, `Back to Home`, and `Try Again` only where reset is available.
- [x] 9.3 Ensure error pages do not show stack traces, framework internals, or scary system wording to shoppers.
- [x] 9.4 Verify error pages are readable and action-visible on mobile without a long scroll.

## 10. Localization And Remaining Public Pages

- [x] 10.1 Add all new rebrand strings to `messages/en.json` and `messages/bg.json`, including hero copy, trust recap copy, category labels, footer group headings, FAQ category labels, error-page copy, and admin labels.
- [x] 10.2 Rebrand the product detail page while preserving gallery, image fallback, product information, price/discount display, stock states, quantity selector, add-to-cart, FAQ links, safety/responsible-party information, comments/reactions where present, loading state, and not-found state.
- [x] 10.3 Rebrand the cart drawer while preserving cart items, quantity controls, remove actions, subtotal, empty state, checkout entry point, optimistic updates, error handling, focus trap, Escape/backdrop close, and badge behavior.
- [x] 10.4 Rebrand checkout with functional low-motion styling while preserving contact fields, delivery/courier flow, office/address selection, shipping price display, payment method behavior, order summary, legal/privacy disclosures, validation, submission, loading, and error handling.
- [x] 10.5 Rebrand the contact page while preserving direct contact/social links, form fields, validation, privacy notice, submit action, success state, and error state.
- [x] 10.6 Rebrand the atelier/about page while preserving CMS-managed section ordering, render types, anchors, images/fallbacks, CTAs, cards/timeline/collections, and structured data.
- [x] 10.7 Rebrand account, orders, order detail, order confirmation, and retry-payment pages while preserving auth prompts, profile details, order list/detail, status timeline, payment status/retry flows, loading states, empty states, and error states.
- [x] 10.8 Rebrand terms, privacy, and cookies pages while preserving legal/policy content, section navigation, anchors, policy links, cookie inventory, and trader/contact discoverability.
- [x] 10.9 Verify final logo/brand-mark behavior: use the signature `M` asset if available, never use a candle as the main logo, and fall back to accessible `Atelier Marie` text when the mark is not available.
- [x] 10.10 Review rebranded public pages against the visual mood guardrails: romantic, soft, elegant, glassy, semi-transparent, corporate, handmade/boutique, and not childish, loud, card-heavy, or commerce-obscuring.

## 11. Tests And Verification

- [x] 11.1 Update unit/component tests for design tokens, footer links, homepage categories, products deep-link filters, FAQ categories/accordions, admin layout, localization, remaining public page preservation, and error pages.
- [x] 11.2 Add preservation tests for existing header/footer controls, product browsing, product detail, product cards, cart/checkout entry points, account/order links, legal/support links, and admin routes touched by the rebrand.
- [x] 11.3 Run frontend lint/type/test checks for the changed frontend package.
- [x] 11.4 Run backend tests only if product category/type data, API contracts, or route behavior changes.
- [x] 11.5 Run Playwright visual/interaction checks on mobile and desktop for homepage, products, product detail, cart drawer, checkout, FAQ, footer, contact, account/orders, legal pages, 404/error, and representative admin pages.
- [x] 11.6 Verify reduced-motion behavior across homepage, product cards, cart drawer, checkout, FAQ accordions, footer, and admin.
- [x] 11.7 Perform a final hardcoded-color scan on touched frontend files.
- [x] 11.8 Perform a final functionality preservation walkthrough before marking the rebrand complete.
- [x] 11.9 Perform a final notes-to-OpenSpec coverage audit against `docs/atelier-marie-ui-notes.md` before considering implementation complete.
