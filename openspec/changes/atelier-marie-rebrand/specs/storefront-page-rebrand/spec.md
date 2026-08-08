## ADDED Requirements

### Requirement: Storefront brand mood and composition
The storefront rebrand SHALL express a romantic, soft, elegant, warm, handmade/boutique mood while avoiding corporate, childish, loud, card-heavy, or purely decorative layouts. Product and atelier photography SHALL carry the emotional signal where available, and shopping actions SHALL remain clear, readable, and easy to use.

#### Scenario: Public pages follow brand mood guardrails
- **WHEN** a public storefront page is rebranded
- **THEN** it uses the Atelier Marie palette, typography, spacing, and imagery in a way that feels romantic, soft, elegant, warm, and handmade/boutique
- **AND** it does not use loud, childish, corporate, or generic marketing-page composition

#### Scenario: Typography roles remain readable
- **WHEN** display or script typography is used for brand moments
- **THEN** product cards, navigation, forms, prices, body copy, and legal/support text continue to use practical readable typography
- **AND** script styling is used sparingly and does not reduce legibility

#### Scenario: Aesthetic treatment does not hide commerce
- **WHEN** a shopper uses a rebranded public page
- **THEN** prices, CTAs, filters, forms, legal disclosures, product details, and recovery actions remain visible and usable

### Requirement: Non-home public pages use the rebrand without losing workflows
The system SHALL align non-home public storefront pages with the Atelier Marie rebrand while preserving every exposed workflow, route, action, state, and legal/support path. Visual updates SHALL use the central token system and SHALL NOT remove existing functionality.

#### Scenario: Product detail page preserves commerce and trust content
- **WHEN** a product detail page renders after the rebrand
- **THEN** the product gallery, image fallback, product name, description, price/discount display, category/materials/crafting details, stock/out-of-stock behavior, quantity selector, add-to-cart action, contextual FAQ links, product safety/responsible-party information, comments/reactions where present, loading state, and not-found state remain available

#### Scenario: Cart drawer preserves shopping workflow
- **WHEN** the cart drawer renders after the rebrand
- **THEN** cart items, quantities, remove actions, subtotal, empty state, checkout entry point, optimistic update behavior, error handling, focus trap, Escape/backdrop close, and cart badge behavior remain available

#### Scenario: Checkout preserves critical order workflow
- **WHEN** checkout renders after the rebrand
- **THEN** contact fields, delivery/courier steps, office/address selection, shipping price display, payment method behavior, order summary, legal/privacy disclosures, validation, submission, loading, and error handling remain available
- **AND** decorative animations do not delay or obscure checkout actions

### Requirement: Support, account, and legal pages keep their purpose clear
The contact, atelier/about, account, orders, terms, privacy, cookies, and auth-related pages SHALL receive rebrand styling only in ways that preserve their primary purpose and required information.

#### Scenario: Contact page remains actionable
- **WHEN** the contact page renders after the rebrand
- **THEN** contact copy, direct contact/social links, form fields, validation, privacy notice, submit action, success state, and error state remain visible and usable

#### Scenario: Atelier page preserves managed sections
- **WHEN** the atelier/about page renders after the rebrand
- **THEN** all published CMS-managed sections render in order by type with anchors, images/fallbacks, CTAs, cards/timeline/collections, and structured data preserved

#### Scenario: Account and order pages preserve customer recovery paths
- **WHEN** account, orders, order detail, order confirmation, or retry-payment pages render after the rebrand
- **THEN** auth prompts, profile details, order list/detail, status timeline, payment status/retry flows, loading states, empty states, and error states remain available

#### Scenario: Legal pages remain readable and complete
- **WHEN** terms, privacy, or cookie policy pages render after the rebrand
- **THEN** required legal/policy content, section navigation, anchors, policy links, cookie inventory, and contact/trader discoverability remain readable and accessible
- **AND** critical legal text is not hidden behind decorative animation or hard-to-find accordions

### Requirement: Brand identity uses a signature M mark
The rebrand SHALL use a beautiful handmade signature-style letter `M` as the primary brand mark when a logo asset is available. The main logo SHALL NOT be a candle icon. Candle drawings MAY be used for product/category decoration, but SHALL NOT be used as the primary brand mark. The brand mark SHALL fall back to an accessible `Atelier Marie` text wordmark when no final `M` asset exists.

#### Scenario: Signature M mark appears when available
- **WHEN** a final signature `M` logo asset is available
- **THEN** the site can render the `M` mark paired with readable `Atelier Marie` brand text in header, hero, footer, or other appropriate brand placements

#### Scenario: Candle icon is not used as main logo
- **WHEN** the site renders a primary brand/logo placement
- **THEN** it does not use a candle drawing as the main logo mark

#### Scenario: Signature animation has static fallback
- **WHEN** the signature `M` mark uses a draw-on animation
- **THEN** the animation runs subtly and a static variant is used for reduced-motion users and small placements

#### Scenario: Logo asset missing does not break layout
- **WHEN** no final logo asset is available
- **THEN** the site renders an accessible `Atelier Marie` text wordmark without broken image icons or empty logo space

#### Scenario: Brand mark remains readable over media
- **WHEN** brand name/logo content appears over hero or footer media
- **THEN** contrast and spacing keep it readable across supported mobile and desktop viewports
