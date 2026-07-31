# Feature Gaps

Feature gaps are recorded only when current evidence shows a credible need for this candle business.

## Customer Commerce

### REQUIRED - Final customer-facing legal identity

Related finding: CND-001

Evidence: Public Terms and product safety/responsible-party details render values from `LEGAL_IDENTITY`, which currently contains `TODO` values.

Why this business needs it: A small family shop must prove who the seller is before customers trust checkout.

Expected outcome: Legal entity, address, registration, VAT/tax status, responsible-party details, and localized policy wording are final before launch.

### REQUIRED - Real product photography for active products

Related finding: CND-002

Evidence: Current database has 10 active products; 9 have no product image rows and would render placeholders.

Why this business needs it: Candles are sensory and giftable products; customers need to see the product, packaging, size, and presentation.

Expected outcome: Every active product has at least one accurate primary image before customers can buy it.

### REQUIRED - Owner-reviewed product media readiness

Related finding: CND-016

Evidence: The current Lavender Dream listing/PDP gallery displays unrelated pet/document/people imagery from `product_images` rows, with the unrelated pet photo marked primary.

Why this business needs it: Product media can be technically present but commercially wrong. A luxury candle shop needs owner-approved images, not arbitrary uploads, before products are customer-visible.

Expected outcome: Active products cannot be considered launch-ready until their product media is reviewed and approved as accurate, product-specific candle/packaging/gift imagery.

### RECOMMENDED - Clear gift-set browsing path

Related finding: CND-003

Evidence: Gift-style products exist, but current product rows are all typed as `candles` and have no category slug. The listing menu is driven by product type/category.

Why this business needs it: Gift buyers are a credible candle audience and gift sets can increase basket value.

Expected outcome: Customers can browse gift sets/boxes directly from the product listing or a clear collection path.

### REQUIRED - Order-attached gift message workflow

Related finding: CND-015

Evidence: FAQ data tells customers to leave a note with the order and send the gift message through the Contact Form. Checkout already supports order notes, and admin order detail displays those notes, but contact messages are separate from orders.

Why this business needs it: Gifts are a credible candle purchase intent. The message that goes in the box must stay attached to the order the family is packing.

Expected outcome: Customers can add a gift message during checkout, the message is stored on the order, admin fulfillment clearly shows it, and FAQ/contact/checkout copy all describe one consistent flow.

### REQUIRED - Customer-ready product taxonomy labels

Related finding: CND-008

Evidence: Active public labels assigned to products include raw display names such as `gift-set`, `luxury-jar`, `dessert`, and `seasonal`, with missing Bulgarian names that fall back to English.

Why this business needs it: Labels are customer merchandising language. They should make products easier to browse and trust, not expose internal slugs.

Expected outcome: Public product labels, types, and categories use polished English and Bulgarian names everywhere they appear in filters, badges, listings, and detail pages.

### REQUIRED - Product-specific candle specs and care content

Related finding: CND-009

Evidence: Active products have empty safety/care fields. Product pages do not expose structured burn time, dimensions, burn/display suitability, or public weight, while the FAQ tells customers that individual product pages contain this kind of product-specific information.

Why this business needs it: Customers cannot smell or inspect candles online. They need concrete product facts to compare value, understand safe use, and decide whether the candle is right for their home or gift.

Expected outcome: Every active product page includes the agreed minimum candle facts: size/volume or dimensions, materials/wick where relevant, burn time or decorative-only guidance, care instructions, and safety warnings.

### REQUIRED - Real Atelier story imagery

Related finding: CND-021

Evidence: Current published Atelier sections/items have empty `image_id` values, so the public page falls back to hard-coded static WebP files that are all `1x1` images.

Why this business needs it: The About/Atelier page is where an unknown family candle shop proves that the craft, products, and workshop are real.

Expected outcome: Published Atelier visual sections use owner-approved real imagery or an intentional no-image layout; no published section stretches a 1x1 placeholder image.

### REQUIRED - Authentic family/maker story content

Related finding: CND-022

Evidence: Current Atelier copy talks about `our atelier`, handmade design, elegance, and fragrance, but does not identify who makes the candles, where they are made at an appropriate level, or why this family business exists.

Why this business needs it: A family candle business needs concrete trust signals and human differentiation, not generic luxury copy that could fit many template shops.

Expected outcome: The Atelier page clearly explains who is behind the candles, how/where they are made, what is genuinely distinctive, and why customers should trust this small business.

### REQUIRED - Bank transfer instructions on confirmation

Related finding: CND-004

Evidence: The payment integration spec requires bank name, IBAN, BIC, and payment reference on the order confirmation page. Current confirmation page does not render a bank-transfer payment block.

Why this business needs it: If bank transfer is offered, customers need instructions immediately after placing the order so payment is not delayed or missed.

Expected outcome: Pending bank-transfer orders show bank name, IBAN, BIC, amount, and short order ID reference on the immediate confirmation page, order detail, and payment-pending email.

### REQUIRED - Payment-aware order history

Related finding: CND-017

Evidence: Customer order cards render fulfillment status, date, item count, and total, but do not show payment method/status or recovery actions even though order responses include `payment_method` and `payment_status`.

Why this business needs it: Card and bank-transfer recovery should not rely on the family manually chasing customers when the account area can show what still needs payment.

Expected outcome: Customer order history distinguishes fulfillment status from payment status and exposes clear retry/payment-instruction actions for unpaid card or bank-transfer orders.

### REQUIRED - Unavailable cart item recovery

Related finding: CND-010

Evidence: Backend cart responses include unavailable items, but frontend cart types/state/dropdown and checkout do not preserve or display them.

Why this business needs it: Small-batch products can sell out, be deactivated, or be corrected by the owner. Customers need a clear recovery path when that happens.

Expected outcome: Cart drawer and checkout show unavailable cart items with a clear reason and a remove/recover action.

### REQUIRED - Stock-aware cart quantity controls

Related finding: CND-011

Evidence: Cart quantity increment is capped at 10, not at the product's current stock. Current launch data includes a product with stock 8.

Why this business needs it: Limited candle inventory should be explained before customers hit an error.

Expected outcome: Cart controls respect the lower of current stock and the per-item limit, and stock-change errors identify the affected product and available quantity.

### RECOMMENDED - Product thumbnails in cart and checkout summary

Related finding: CND-012

Evidence: Cart and checkout summaries render text, quantity, and price only, despite cart API product data including image fields.

Why this business needs it: Candles are visual and giftable; customers should visually confirm the item before paying.

Expected outcome: Cart drawer and checkout order summary show compact product thumbnails with stable placeholder behavior.

### REQUIRED - Mobile order summary before checkout submit

Related finding: CND-025

Evidence: Mobile checkout renders the primary `Place Order` button before the `Order Summary` card and final `Total` row. Browser metrics from the retained mobile screenshot show the button visible in the viewport before the summary heading appears below the fold.

Why this business needs it: Mobile customers should confirm the final payable total before committing to an order.

Expected outcome: At mobile widths, the order summary/final total appears before or inside the same reviewed block as the primary submit action.

### RECOMMENDED - Free-shipping threshold message in cart

Related finding: CND-013

Evidence: Checkout knows about the EUR 50 free-shipping threshold and shows threshold messaging in the shipping summary, but the cart drawer only shows subtotal and checkout action.

Why this business needs it: A clear threshold message can increase basket value without fake urgency or dark patterns.

Expected outcome: Cart drawer shows `Add EUR X more for free shipping` below threshold and `Free shipping unlocked` at or above threshold.

## Admin Operations

### REQUIRED - Accurate dashboard payment/revenue separation

Related finding: CND-019

Evidence: Admin Dashboard labels `revenue_this_week_cents` as revenue, but the backend sums non-cancelled order totals without filtering by payment status. Current database evidence has unpaid COD-pending orders counted as weekly revenue.

Why this business needs it: The family needs a truthful picture of cash collected versus orders still awaiting payment or delivery collection.

Expected outcome: Dashboard separates paid revenue from unpaid/open order value, and payment-pending/COD-pending/card-failed amounts are clearly identified.

### REQUIRED - Daily admin work queue on dashboard

Related finding: CND-020

Evidence: Backend dashboard data includes order counts by status and low-stock count, but the frontend admin stats type/API/page drop those fields and show only orders today, weekly revenue, and active products.

Why this business needs it: The admin home page should tell a family member what needs action today: orders to confirm, payment attention, packing/shipping, low stock, and customer messages.

Expected outcome: Dashboard shows actionable cards or lists for pending orders, payment attention, ready-to-ship orders, low-stock products, and contact messages needing attention, with links to the relevant filtered admin pages.

### REQUIRED - Owner-visible contact message inbox or recovery path

Related finding: CND-014

Evidence: Contact messages are stored in `contact_messages` and owner notification depends on `admin_notification_email`, which defaults to disabled. If notification is skipped or fails, reviewed evidence found no admin UI/route for seeing those messages.

Why this business needs it: The site uses contact for custom candles, gifts, order support, returns, and damaged items. The family needs a non-developer way to see and recover customer inquiries.

Expected outcome: Admin users can see submitted contact messages and their delivery status, with failed/suppressed messages surfaced as needing attention.

### REQUIRED - Admin mark-paid action for bank-transfer orders

Related finding: CND-005

Evidence: Backend supports marking pending bank-transfer orders paid, but admin UI exposes only status transitions and read-only payment status.

Why this business needs it: If bank transfer is offered, confirming payment received is a routine owner task, not a developer task.

Expected outcome: Admin users can find pending bank-transfer orders, mark payment received, and see the payment status update without leaving the UI.

### REQUIRED - Shipping modal defaults to the order courier

Related finding: CND-006

Evidence: Current database contains Econt orders, but the shipping modal initializes tracking carrier to Speedy and does not receive the order delivery courier.

Why this business needs it: Wrong courier tracking details confuse customers and create avoidable support work.

Expected outcome: The ship modal defaults to the order's delivery courier, displays that courier, and warns or blocks mismatched tracking carriers according to the owner's workflow.

### RECOMMENDED - Owner-visible shipping policy controls

Related finding: CND-018

Evidence: Admin Delivery controls courier/method availability only. Free-shipping threshold, fallback shipping amount, packaging buffer, and shipping maximum are code constants mirrored between backend and frontend, while banner copy is admin-managed separately.

Why this business needs it: The family may need to adjust shipping thresholds or fallback delivery charges when courier prices, margins, or seasonal offers change.

Expected outcome: Admin Delivery shows the active free-shipping threshold and fallback shipping amount. These values are either owner-editable or clearly fixed from one backend source of truth, and storefront messaging cannot drift from checkout rules.

### REQUIRED - Active-product media readiness guard

Related findings: CND-002, CND-007

Evidence: The current catalog contains active products without images. The Admin Products list marks every product Active but shows no media/readiness column or warning for image-less products. The admin create flow saves the product first with `is_active` from the form, then uploads images through separate requests, so an upload failure can leave the newly created product active without media.

Why this business needs it: A family member should not accidentally publish an image-less product and make the shop look unfinished.

Expected outcome: Admin product list/form clearly flags active products missing primary media. Creating or activating a product with zero images is blocked, warned, or automatically kept inactive according to the owner-approved publishing rule; media upload failure cannot leave an unintended customer-visible placeholder product.

### RECOMMENDED - Draft-safe admin content publishing

Related finding: CND-023

Evidence: New Atelier items and FAQ items are inserted as published by default, while the admin create forms do not offer a hidden/draft choice before creation.

Why this business needs it: The family should be able to add FAQ/story/collection content without accidentally making unfinished text live on the storefront.

Expected outcome: New admin-managed FAQ and Atelier items default to hidden/draft or require an explicit publish-now choice, with a simple way to preview or verify public rendering before publishing.

### RECOMMENDED - Navigable admin content editors

Related finding: CND-026

Evidence: Retained admin screenshots show the Atelier content editor is 27,202px tall on 390px mobile and the FAQ editor is 19,322px tall, with every section/item expanded into full edit forms.

Why this business needs it: A family member should be able to update one FAQ answer or story section without scrolling through a massive wall of bilingual fields and repeated controls.

Expected outcome: Admin FAQ and Atelier editors provide compact summaries, collapsible sections/items, anchors, search/filtering, or focused edit mode so targeted edits are comfortable on desktop and mobile.

### RECOMMENDED - Owner-safe product CSV import guidance

Related finding: CND-028

Evidence: Admin Products shows an owner-facing CSV reference that points to `POST /v1/admin/products/import`, falsely lists `category` and `stock` as required, and uses `Floral`/`Woody` as category examples even though the backend now requires only `id`, `name_en` or `name`, and `price_cents`, and taxonomy fields use managed slugs.

Why this business needs it: Bulk catalog edits are useful only if the family can follow the instructions safely. A stale template can break seasonal product launches or create bad merchandising data across many products at once.

Expected outcome: If CSV import remains owner-facing, the admin provides accurate required/optional columns, valid taxonomy-slug examples, and an upload/template flow or clear validation path. If CSV import is developer-only, the API reference is removed from normal owner-facing admin screens.

### RECOMMENDED - Safe destructive actions for admin content

Related finding: CND-027

Evidence: Admin FAQ and Atelier delete buttons call hard-delete APIs directly, and the backend permanently deletes `faq_items` and `about_items` rows.

Why this business needs it: The owner should not permanently lose public FAQ/story content through a single accidental click.

Expected outcome: FAQ and Atelier deletes require explicit confirmation and provide undo, soft-delete/restore, or a documented owner-accessible recovery path.

### NEEDS DISCUSSION - Taxonomy assignment guidance for gift sets/boxes

Related finding: CND-003

Evidence: Product type `boxes` exists, but current gift-set products are assigned to `candles`.

Why this business may need it: The admin may need clearer guidance on when to use product type, category, or label so storefront filters match business merchandising.

Expected outcome: Owner confirms the intended taxonomy model; admin labels and defaults then make that model hard to misuse.

## Marketing

No evaluated gaps yet.

## Analytics

No evaluated gaps yet.

## Accessibility

### REQUIRED - Programmatic labels for checkout delivery fields

Related findings: QA-040, CND-024

Evidence: Checkout delivery fields show visible labels, but the live DOM has no `id`/`htmlFor`, `aria-label`, or `aria-labelledby` association for door city, postcode, street, building, apartment, and phone fields. Chrome's accessibility tree names those fields from placeholders/current values such as `e.g., Sofia`, `1000`, and `+359...` instead of the visible labels.

Why this business needs it: Delivery details are mandatory checkout inputs. Customers using screen readers or voice input need the same clear field names as sighted mouse/touch users.

Expected outcome: Every office and door delivery field is programmatically labelled by its visible label, placeholders remain examples only, and validation errors are associated with the affected field.

### RECOMMENDED - Cart drawer error controls meet mobile target-size rules

Related finding: QA-039

Evidence: Mobile cart screenshot/metrics after a stock error show the `Dismiss error` button is 16x16 pixels, while the main drawer close button uses a 44x44 target.

Why this business needs it: Customers need to recover from cart errors without precision tapping, especially on mobile where most checkout friction happens.

Expected outcome: Cart error dismiss controls use the same minimum touch-target sizing and focus-visible styling as other icon buttons.

## Technical / Resilience

No evaluated gaps yet.

## Status Definitions

- REQUIRED: Needed for launch or core operation.
- RECOMMENDED: Important, but not necessarily launch-blocking.
- OPTIONAL: Useful if the business can support it.
- NOT APPLICABLE: Considered and rejected for this business.
- NEEDS DISCUSSION: Business context is missing.

## Review History

### 2026-07-31

- Created feature gap tracking file.
- Added gaps related to legal identity, product photography, active-product media warnings, and gift-set taxonomy/merchandising.
- Added bank-transfer confirmation instruction gap.
- Added admin bank-transfer payment handling and shipping-carrier readiness gaps.
- Upgraded active-product media readiness from recommended warning to required guard after reviewing the partial product-create/media-upload workflow.
- Added required gaps for customer-ready taxonomy labels and product-specific candle specs/care content.
- Added cart gaps for unavailable-item recovery, stock-aware quantity controls, product thumbnails, and free-shipping threshold messaging.
- Added contact/gifting gaps for owner-visible contact-message recovery and an order-attached gift-message workflow.
- Added payment-aware order-history gap for customer recovery of unpaid card and bank-transfer orders.
- Added owner-visible shipping policy gap for free-shipping/fallback shipping controls and storefront consistency.
- Added admin dashboard gaps for accurate payment/revenue separation and daily work-queue visibility.
- Added Atelier/FAQ content gaps for real story imagery, authentic family/maker copy, and draft-safe admin publishing.
- Added checkout accessibility gap for programmatic labels on delivery fields.
- Added mobile checkout gap requiring the order summary/final total before the submit action.
- Added admin content gaps for navigable long-form editors and safe destructive delete actions.
- Added owner-safe product CSV import guidance gap after reviewing Admin Products screenshots and backend import behavior.
