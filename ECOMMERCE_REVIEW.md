# E-Commerce Review

## Project Context

Known business information from current implementation evidence:

- Atelier Marie is described in project docs as a luxury handcrafted candle e-commerce platform for a small family business.
- The current database contains 10 active customer-facing products priced from EUR 26.00 to EUR 52.00.
- Current products include individual candles plus gift-style products such as Winter Spice Trio and Spring Blossom Duo.
- Current product data mentions soy wax, coconut wax, coconut-soy blend, essential oils, fragrance oils, cotton wick, ceramic vessels, and 2-5 days to craft.
- The implementation includes English and Bulgarian storefront content, cart, checkout, orders, account, contact, FAQ, Terms, privacy/cookies, admin products, admin orders, delivery settings, promotions, analytics, and editable atelier/FAQ content.
- Delivery implementation references Speedy and Econt; payment text/code references Stripe, cash on delivery, and bank transfer. Final business support for these still needs owner confirmation.

Still missing owner-confirmed context:

- Final legal business identity, address, registration, VAT/tax status, and responsible-party details.
- Whether the current database is production catalog data or sample/staging data.
- Final target customers, bestseller list, shipping regions, delivery promises, payment methods, return handling, damaged-item handling, custom/personalized candle policy, corporate/bulk-order policy, and daily admin capacity.

## Review Summary

- Total findings: 28
- Open blockers: 3
- Open high-priority issues: 18
- Medium issues: 6
- Low issues: 0
- Opportunities: 1
- Verified findings: 0

## Current Launch Verdict

REJECTED

Reason: I would not pay final acceptance yet. The customer-facing legal identity still exposes placeholder values, most active products have no real product photography, and the only active product gallery currently reviewed shows unrelated pet/document imagery instead of candles. The Atelier page also relies on 1x1 placeholder image files and generic story copy that does not identify the actual family, makers, or place behind the business. The admin product workflow can create active products before media upload succeeds, admin-managed content can be created live without a draft/preview step, and content editors are unwieldy on mobile with destructive delete actions that lack confirmation. Customer-facing taxonomy labels, product-specific candle care/spec content, cart recovery, contact/gift-message operations, payment recovery, checkout delivery-field accessibility, mobile checkout order review, admin product bulk-import guidance, and admin dashboard operations also feel unfinished. A small candle business cannot launch with legal TODOs, image-less products, misleading product images, placeholder story imagery, raw merchandising data, hidden cart availability problems, owner inquiries or gift requests that can be missed, order history that hides whether payment still needs action, and a dashboard that can call unpaid orders revenue while hiding the daily work queue.

## Findings

### CND-001

Title: Customer-facing legal identity still contains TODO placeholders

Status: OPEN

Priority: BLOCKER

Area: Trust / Legal / Checkout

Page/Screen: Terms & Conditions; Product Detail safety section

Evidence: `frontend/lib/legal.ts` contains `TODO: legal entity name`, `TODO: geographic business address`, `TODO: registration number`, `TODO: VAT number or not VAT registered`, and `TODO: geographic business address` for responsible party. `frontend/app/[locale]/terms/page.tsx` renders those `LEGAL_IDENTITY` values directly in the public Terms page. `frontend/messages/en.json` also says the identity details are placeholders and must be reviewed before launch.

Problem: Customers can see that the trader/legal identity is unfinished. Product safety information also depends on the same incomplete responsible-party address.

Why it matters: A small unknown shop has to prove it is legitimate. Visible legal placeholders immediately reduce trust and may create legal/compliance exposure.

Customer impact: A cautious customer may abandon checkout because the seller identity looks incomplete or fake.

Business impact: Lost sales, lower trust, possible compliance risk, and avoidable support questions.

Admin impact, if applicable: The owner cannot fix this through ordinary admin content unless these values are configurable elsewhere; this likely requires a developer or deployment config change.

Recommended change: Replace all legal placeholder values with owner-confirmed legal entity, geographic address, registration number, VAT/tax status, and responsible-party address. Remove customer-facing placeholder wording once reviewed.

Acceptance criteria: No public page, checkout agreement, footer/legal page, product safety section, or localized policy text displays `TODO`, placeholder wording, or unreviewed legal identity language. The owner has confirmed the final legal details for English and Bulgarian pages.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: This is a launch blocker regardless of visual polish.

### CND-002

Title: Most active products have no real product photography

Status: OPEN

Priority: BLOCKER

Area: Product Discovery / Merchandising / Trust

Page/Screen: Product Listing; Product Detail

Evidence: Current database query shows 10 active products, but only `lavender-dream-300ml` has product image rows. The other 9 active products have `image_count = 0`. `frontend/components/products/ProductImage.tsx` renders a branded placeholder with the product name when `imageUrl` is missing or fails. Retained Admin Products screenshots show the product list columns as name, category, price, stock, status, and actions only; every row is marked `Active`, but there is no image/media/readiness column or warning for active products with zero images.

Problem: Customers browsing the current active catalog would mostly see placeholders instead of photos.

Why it matters: Candles are visual and sensory products. Customers cannot smell them online, so photography, packaging, wax/container appearance, scale, and gift presentation carry much of the sales work.

Customer impact: Products feel unfinished, less desirable, and harder to compare or trust.

Business impact: Lower conversion, weaker gift appeal, and a cheaper overall impression of the shop.

Admin impact, if applicable: The admin workflow appears able to publish active products without images, so the family can accidentally create a storefront full of placeholders.

Recommended change: Add accurate product photography for every active customer-facing product before launch. At minimum, each active product needs one primary photo; gift sets should show packaging and contents. Consider an admin warning or publish checklist for active products missing media.

Acceptance criteria: Every active product visible to customers has at least one accurate primary image. Product listing and detail pages show real images, not placeholders, for all active products. Admin users can easily identify active products missing required media before launch or publication.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: If the current database is only sample/staging data, this still becomes a production readiness gate: no active production product should launch without media.

### CND-003

Title: Gift sets are not clearly merchandised as gift products

Status: OPEN

Priority: HIGH

Area: Product Discovery / Gifting / Merchandising

Page/Screen: Product Listing; Product Detail

Evidence: The current database has active gift-style products including `winter-spice-trio` and `spring-blossom-duo`, and taxonomy contains product type `boxes`. However, every current product row has `product_type_slug = candles`, and `category_slug` is empty. The listing menu builds top-level sections from product type and categories, so the customer-facing product menu will not expose Boxes/Gift Sets as a top-level path from this data.

Problem: Gift sets are treated as ordinary candles in the primary taxonomy instead of being clearly discoverable as gifts or boxes.

Why it matters: Gifting is a major candle purchase intent. If a customer wants a birthday, holiday, housewarming, or thank-you gift, the shop should make that path obvious.

Customer impact: Gift buyers must notice specific product names or labels instead of being guided to a clear gift-set collection.

Business impact: Missed upsell and basket-size opportunity; weak seasonal/gift merchandising.

Admin impact, if applicable: The owner may think creating a gift-set product is enough, while the storefront still hides it under generic candle browsing.

Recommended change: Decide the intended taxonomy and apply it consistently. Gift sets should either use a clear product type such as Boxes/Gift Sets or a polished customer-facing collection/category. Product detail badges should not imply that a set/box is merely a single candle.

Acceptance criteria: A customer can intentionally browse gift sets/boxes from the product listing without relying on search. Gift products have clear customer-facing taxonomy labels in English and Bulgarian. Product detail badges accurately reflect gift-set/box products.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: This is not a request for complex personalization or bundles. It is basic merchandising for products already present in the catalog.

### CND-004

Title: Bank transfer instructions are missing from the immediate confirmation page

Status: OPEN

Priority: HIGH

Area: Checkout / Payment / Customer Instructions

Page/Screen: Order Confirmation

Evidence: `openspec/changes/payment-integration/specs/bank-transfer-instructions/spec.md` requires IBAN, BIC, bank name, and short order ID payment reference on the order confirmation page for `payment_method='bank_transfer'`. The checkout page can offer bank transfer when `NEXT_PUBLIC_BANK_IBAN` is configured. The order detail page renders bank instructions for pending bank-transfer orders, but `frontend/app/[locale]/orders/[id]/confirmation/page.tsx` only renders the generic thank-you message, items, totals, policy links, contact note, delivery details, and continue-shopping button.

Problem: A customer who chooses bank transfer may land on the immediate confirmation page without seeing the payment details needed to complete payment.

Why it matters: Bank transfer depends on the customer copying the correct bank details and reference. Hiding that information on the first post-purchase screen creates payment delays and support work.

Customer impact: The customer may think the order is complete, miss the transfer step, or have to search elsewhere for payment instructions.

Business impact: Unpaid orders, delayed fulfillment, manual follow-up, and avoidable abandoned revenue.

Admin impact, if applicable: The family may need to chase customers manually or reconcile transfers with weak/missing references.

Recommended change: Show a payment block on the confirmation page. For bank-transfer orders with pending payment, display bank name, IBAN, BIC, amount, and the short order ID reference. For card orders with pending/failed payment, show a clear retry-payment action. Avoid a generic “Thank you” state that hides unpaid status.

Acceptance criteria: A bank-transfer customer sees the bank name, IBAN, BIC, amount, and short order ID payment reference on the immediate confirmation page. The same details remain available on order detail and in the payment-pending email. Automated coverage proves the confirmation-page scenario.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: The local `.env.local` does not currently enable bank transfer, but the feature exists, is documented, and has an explicit spec requirement for the confirmation page.

### CND-005

Title: Admin UI does not let the owner mark bank-transfer orders as paid

Status: OPEN

Priority: HIGH

Area: Admin Orders / Payment Operations

Page/Screen: Admin Orders; Admin Order Detail

Evidence: The backend exposes `PATCH /v1/admin/orders/{order_id}/payment` to mark a pending bank-transfer order paid, and `GET /v1/admin/orders` supports a `payment_status` filter. `frontend/lib/api.ts` only exposes `getAdminOrders`, `getAdminOrder`, and `updateOrderStatus` for admin orders; there is no frontend API wrapper for marking payment paid. The admin orders page imports only `getAdminOrders` and `updateOrderStatus`, shows payment method/status as read-only text, and the only action control is order-status transition. The admin order detail page is also read-only for payment/status operations.

Problem: If bank transfer is offered, the family cannot complete the payment workflow from the admin UI.

Why it matters: Bank transfer requires a human to confirm money arrived. If that action is API-only, routine order processing depends on a developer, script, or manual database/API call.

Customer impact: Paid orders may remain marked as awaiting payment, delaying production, dispatch, and customer confidence.

Business impact: Unpaid/paid order state becomes unreliable, revenue reconciliation gets harder, and the business may send the wrong customer emails.

Admin impact, if applicable: The owner cannot handle a normal bank-transfer order at 9pm without technical help.

Recommended change: Add an admin UI action for pending bank-transfer orders to mark payment received. Add a payment-status filter or “needs payment attention” view so unpaid bank-transfer/card orders are easy to find. Keep the existing backend validation and show a clear confirmation/error state.

Acceptance criteria: A pending bank-transfer order can be found from the admin orders UI and marked paid without using an API client or developer tool. The UI updates payment status to paid, queues/surfaces the correct customer email behavior, and prevents the action for COD/card/already-paid orders with a clear message.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: This matters if bank transfer remains a launch payment method. If bank transfer is not offered at launch, mark this finding WON'T FIX or lower priority only after owner confirmation.

### CND-006

Title: Shipping modal defaults to Speedy even for non-Speedy orders

Status: OPEN

Priority: HIGH

Area: Admin Orders / Shipping Operations

Page/Screen: Admin Orders shipping modal

Evidence: Current database orders include Econt delivery orders. The admin orders list shows each order's delivery courier, but `ShipOrderModal` initializes `carrier` with `useState("speedy")` and receives only `orderId`, `isSubmitting`, `onCancel`, and `onConfirm`. When the admin confirms shipping, that selected carrier is sent as `tracking_carrier`. The backend then persists the submitted tracking carrier and auto-generates the tracking URL from it.

Problem: An Econt order can be marked shipped with a Speedy tracking carrier by default if the admin simply enters the tracking number and confirms.

Why it matters: Courier/tracking details go into the order record and shipped customer email. A wrong carrier or tracking link makes the business look careless and increases support work.

Customer impact: The customer may receive a tracking link for the wrong courier and be unable to track the parcel.

Business impact: More “where is my order?” messages, delivery confusion, and possible fulfillment mistakes.

Admin impact, if applicable: The owner must remember to manually change the carrier every time, even though the order already knows which courier the customer selected.

Recommended change: Pass the order's delivery courier into the shipping modal and default the tracking carrier to that courier when known. Show the selected delivery courier inside the modal. Warn or require confirmation if the tracking carrier differs from the order delivery courier. For Speedy orders, decide whether the UI should support backend waybill automation instead of forcing a manual tracking number.

Acceptance criteria: Opening the ship modal for an Econt order defaults carrier to Econt; opening it for a Speedy order defaults to Speedy. The modal displays the customer's selected delivery courier. Saving a mismatched carrier requires an explicit warning/confirmation or is blocked according to the owner's workflow. Automated coverage proves the default behavior.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: This is operationally risky because the current database already contains Econt orders.

### CND-007

Title: Product creation can leave an active product published when media upload fails

Status: OPEN

Priority: HIGH

Area: Admin Products / Product Publishing / Merchandising Operations

Page/Screen: Admin Products create/edit flow

Evidence: `frontend/components/admin/ProductForm.tsx` defaults new products to `is_active = true`, validates required text/price/type/stock/weight, and validates selected image file type/size, but does not require an image before an active product can be submitted. `frontend/app/[locale]/admin/products/new/page.tsx` first calls `createProduct(...)` with `is_active: data.is_active`, then uploads each image through `uploadProductImage(product.id, file)`. `app/models/products.py` defaults `CreateProductRequest.is_active` to `True`. `app/services/product_service.py` inserts the product row with `is_active` from the create payload and returns it before any image rows are added. The image upload endpoint is a separate request and can fail with file too large, invalid type, processing failure, product not found, or image limit errors. Retained create/edit screenshots show `Active (visible in the store)` checked by default and `Product images` presented as a file chooser, without a visible warning that an active product with no image will publish as a placeholder.

Problem: A family member can submit a new active product with photos selected, hit a media upload failure after the product is already created, and end up with an active storefront product that has no product image.

Why it matters: The owner sees a save error, but the business state is already partially changed. This is exactly how unfinished products leak into a live candle shop.

Customer impact: Customers may see a new product with a branded placeholder instead of real candle photography, which makes the shop feel unfinished and less trustworthy.

Business impact: Lost conversion, weaker product desirability, and avoidable cleanup before seasonal or gift launches.

Admin impact, if applicable: The owner must notice the partial create, find the product, understand that it may already be active, and manually fix or deactivate it. That is too fragile for routine product entry.

Recommended change: Make product publishing media-aware. Either create products inactive/draft until required media upload succeeds, or block `is_active=true` unless the product has at least one primary image. If upload fails after create, clearly state whether the product was created and automatically keep/deactivate it as inactive until media is fixed.

Acceptance criteria: Creating a new active product cannot leave a customer-visible product with zero images because of a media upload failure. Failed media upload either rolls back the product create or leaves the product inactive with a clear admin recovery message. Editing/activating an existing product with zero images is blocked or explicitly warned according to the owner's agreed publishing rule. Automated coverage proves the partial-create failure path.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: This is related to CND-002 but distinct: CND-002 is the current catalog/customer impact; CND-007 is the admin workflow that can recreate the problem.

### CND-008

Title: Customer-facing product labels expose raw internal slug-style names

Status: OPEN

Priority: HIGH

Area: Product Discovery / Merchandising / Localization

Page/Screen: Product Listing filter menu; Product Detail badges

Evidence: Current `product_labels` rows used by active products include public active terms with `name_en` values `dessert`, `gift-set`, `luxury-jar`, and `seasonal`, with empty `name_bg` values. Every active product currently carries one of those labels. `app/services/taxonomy_service.py` exposes active label names through public taxonomy and falls back to English when Bulgarian is missing. `frontend/components/products/ProductListingClient.tsx` renders visible label names in the customer filter menu, and `frontend/app/[locale]/products/[id]/page.tsx` renders each product label name as a visible badge on the product page.

Problem: Customers can see lowercase, hyphenated, admin-style labels instead of polished merchandising names such as `Gift set`, `Luxury jar`, `Seasonal`, and Bulgarian equivalents.

Why it matters: This makes the shop feel unfinished and data-driven in the wrong way. A family candle business needs labels to help customers browse by mood, gift intent, season, or collection, not expose implementation slugs.

Customer impact: Browsing feels less polished and less trustworthy, especially in Bulgarian where the missing names fall back to English slug-style labels.

Business impact: Weakened merchandising, weaker gift navigation, and a cheaper impression of the brand.

Admin impact, if applicable: The owner may not realize that a taxonomy term's display name is shown directly to customers in filters and product badges.

Recommended change: Replace raw label display names with customer-ready English and Bulgarian names. Audit every active public product type, category, and label for launch-quality wording. Keep slugs internal; expose only polished display names to customers.

Acceptance criteria: No customer-facing product filter, badge, listing, or detail page displays lowercase slug-style labels such as `gift-set`, `luxury-jar`, or `dessert`. Active labels have reviewed English and Bulgarian display names. Gift labels support, rather than undermine, the gift-set merchandising path in CND-003.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: This overlaps with CND-003 but is not limited to gift sets; it affects every active product through labels.

### CND-009

Title: Product pages lack product-specific candle safety, care, and comparison details

Status: OPEN

Priority: HIGH

Area: Product Detail / Product Content / Customer Confidence

Page/Screen: Product Detail; FAQ

Evidence: Current active products all have empty `safety_warnings_en` and `care_instructions_en` fields. `frontend/app/[locale]/products/[id]/page.tsx` only renders safety warnings and care instructions when those fields are present. The same page renders materials and crafting time, but does not expose weight, dimensions, burn time, burn suitability, or wick details as structured product facts. `app/models/products.py` exposes `weight_grams` only in `ProductAdminResponse`, not in the public `ProductResponse`. The FAQ tells customers that exact wax, wick information, sizes/dimensions/weight, burn suitability, recommended burn times, and preparation times are on individual product pages, but the current product pages do not provide most of that product-specific information.

Problem: Product pages ask customers to buy sensory, safety-sensitive candle products without enough product-specific facts to compare value, understand use, or know how to burn/display the candle safely.

Why it matters: Candles are not generic objects. Customers need to understand size, burn time, wick/materials, care, and safe use before buying, especially when the FAQ sends them back to product pages for those details.

Customer impact: Customers may hesitate because they cannot judge value, expected use, burn behavior, or care requirements. Decorative candles versus burnable candles are especially unclear.

Business impact: Lower conversion, more pre-sale questions, more misuse risk, and weaker trust in product quality.

Admin impact, if applicable: The admin form has optional safety/care fields, but the current catalog leaves them blank and there is no evident readiness guard for missing candle-specific content.

Recommended change: Define a minimal product-content standard for launch. Each active candle should show product-specific size/volume or dimensions, approximate burn time or burn/display suitability, wick/material notes where relevant, care instructions, and safety warnings. The FAQ should match what product pages actually provide.

Acceptance criteria: Every active product page gives customers enough product-specific information to compare and safely use the candle: size/volume or dimensions, materials/wick where relevant, burn time or decorative-only guidance, care instructions, and safety warnings. FAQ claims about product-page details are true for the active catalog. Admin product entry flags missing required content before publication.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: This is not a request for complex variants. It is basic candle product content that reduces hesitation and support questions.

### CND-010

Title: Cart frontend drops unavailable cart items returned by the backend

Status: OPEN

Priority: HIGH

Area: Cart / Availability Recovery / Checkout Readiness

Page/Screen: Cart Drawer; Checkout

Evidence: `app/models/cart.py` defines `CartResponse.unavailable_items`, and `app/services/cart_service.py` separates deleted or inactive cart products into `unavailable_items` with a reason. `app/routes/cart.py` returns those unavailable items in the API response. However, `frontend/lib/types.ts` defines `CartResponse` with only `items`, `total_cents`, and `item_count`; `frontend/contexts/CartContext.tsx` stores only those same fields; `frontend/components/cart/CartDrawer.tsx` renders only active `items` and treats `item_count === 0` as an empty cart. `frontend/app/[locale]/checkout/page.tsx` also redirects to products when `items.length === 0` and has no access to unavailable items.

Problem: If a product in the customer's cart is deleted or deactivated after being added, the backend can report it, but the customer-facing cart ignores that information.

Why it matters: Product availability changes are normal for a small candle business with limited stock and seasonal items. The cart must explain what changed and let the customer recover.

Customer impact: The customer may see an apparently empty cart, or a cart missing one item, without understanding that a product became unavailable.

Business impact: Lost sales, confusion, and support questions at the worst point in the buying flow.

Admin impact, if applicable: The family may get messages from customers who think the cart lost items or the site is broken.

Recommended change: Carry `unavailable_items` through frontend types, cart state, cart drawer, and checkout. Show a clear message naming the unavailable product and reason, and provide a remove action plus a link back to products or related alternatives.

Acceptance criteria: When a cart contains a deactivated or deleted product, the cart drawer and checkout show a clear unavailable-item notice instead of silently hiding it. The customer can remove the stale item without developer help. Automated coverage proves mixed active/unavailable and unavailable-only cart states.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: The checkout messages already include unavailable-item wording, but the current cart context does not preserve the data needed to use it.

### CND-011

Title: Cart quantity controls ignore product stock and force avoidable stock errors

Status: OPEN

Priority: HIGH

Area: Cart / Inventory / Customer Recovery

Page/Screen: Cart Drawer; Checkout

Evidence: `frontend/components/cart/CartItem.tsx` sets `canIncrement = quantity < 10`, independent of `item.product.stock`. Current active catalog data includes `honey-tobacco-oak-300ml` with stock 8. If that item is in the cart at quantity 8, the cart plus button is still enabled because 8 is below 10. The backend then rejects quantity 9 in `app/services/cart_service.py` because requested quantity exceeds product stock, and the frontend maps that to the generic `INSUFFICIENT_STOCK` message.

Problem: The cart allows customers to attempt quantities the system already knows are unavailable.

Why it matters: Stock limits should be communicated before the customer hits an error. This matters for small-batch candle inventory where low stock is plausible.

Customer impact: The customer presses plus, gets a generic stock error, and has to infer what quantity is actually allowed.

Business impact: Checkout friction, avoidable error states, and weaker confidence in inventory accuracy.

Admin impact, if applicable: The family may receive questions about whether an item is actually available or how many can be ordered.

Recommended change: Make cart quantity controls stock-aware. Disable increment at `min(product.stock, cart_max_quantity_per_item)`, show available quantity when the customer reaches the limit, and display product-specific stock errors using backend details when a race still occurs.

Acceptance criteria: A cart item with stock 8 cannot be incremented beyond 8 from the UI. If stock changes after the cart loads, the customer sees a product-specific message with the available quantity and can update or remove the item. Automated coverage proves stock below the per-item cap and stock-change rejection paths.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: This is separate from backend stock protection, which exists. The issue is customer-facing recoverability.

### CND-012

Title: Cart and checkout summary do not show product images

Status: OPEN

Priority: MEDIUM

Area: Cart / Checkout Confidence / Visual Confirmation

Page/Screen: Cart Drawer; Checkout order summary

Evidence: Cart API items include embedded product image fields through `ProductResponse`. `frontend/components/cart/CartItem.tsx` renders product name, price, quantity controls, line total, and remove action, but no image thumbnail. `frontend/app/[locale]/checkout/page.tsx` renders order-summary rows with product name, quantity, price, and line total, but no product image.

Problem: Customers cannot visually confirm the candle or gift set they are about to buy from the cart or checkout summary.

Why it matters: Candles are visual, decorative, and giftable products. The product image helps customers confirm they selected the right style, packaging, or set before paying.

Customer impact: Higher risk of uncertainty or wrong-product hesitation, especially when multiple products have similar scent-style names.

Business impact: Lower checkout confidence and more avoidable order-change questions.

Admin impact, if applicable: If customers order the wrong item, the family handles the correction manually.

Recommended change: Show a compact product thumbnail for each cart and checkout-summary line. Use the product primary thumbnail when available and the same fallback behavior as product cards when not.

Acceptance criteria: Cart drawer and checkout summary show a stable thumbnail for every line item on desktop and mobile. Missing images still render a polished placeholder, but launch readiness remains governed by CND-002.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: This does not replace CND-002. Real catalog photography is still required.

### CND-013

Title: Cart misses an obvious free-shipping threshold upsell

Status: OPEN

Priority: OPPORTUNITY

Area: Cart / Conversion / Merchandising

Page/Screen: Cart Drawer

Evidence: `frontend/lib/constants.ts` mirrors a EUR 50 free-shipping threshold, and checkout's `ShippingPriceSummary` uses that threshold to show `Add {amount} more for free shipping` or `You've unlocked free shipping!`. `frontend/components/cart/CartDrawer.tsx` only shows subtotal and `Proceed to Checkout`; it does not tell the customer how close they are to free shipping or that they have unlocked it.

Problem: The cart does not use a known commercial incentive at the moment when customers are deciding whether to add one more candle.

Why it matters: Candle purchases are naturally basket-buildable. If a customer is EUR 8-20 short of free shipping, a clear cart message can encourage a second candle, wax item, or gift set without manipulation.

Customer impact: Customers may miss a legitimate way to get better value from delivery.

Business impact: Missed average-order-value opportunity.

Admin impact, if applicable: None direct.

Recommended change: Add a restrained cart message such as `Add EUR X more for free shipping` below the subtotal, and `Free shipping unlocked` once the threshold is met. Link back to products or gift sets if useful.

Acceptance criteria: Cart drawer shows the amount remaining to free shipping when the subtotal is below EUR 50 and confirms free shipping when the threshold is met. The message uses the same server/client threshold as checkout and does not imply fake urgency.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: This is an opportunity, not a launch blocker.

### CND-014

Title: Contact inquiries can be accepted without any owner-facing inbox or recovery view

Status: OPEN

Priority: HIGH

Area: Contact / Customer Support / Admin Operations

Page/Screen: Contact form; Admin contact-message operations

Evidence: The contact page copy invites customers to use the form for custom candles, order questions, and thoughtful gifts. `ContactForm` submits to `/v1/contact`, and `app/routes/contact.py` accepts the message and returns success after `create_contact_message(...)`. `app/services/contact_service.py` persists messages into `contact_messages` with `email_status = 'queued'`. Owner notification depends on `settings.admin_notification_email`, but `app/config.py` defaults that value to an empty string with the comment `empty = admin notifications disabled`; when no recipient is configured, `_process_contact_row(...)` marks the row `skipped_suppressed` with `error="no recipient configured"`. Repository search found public contact submission code and contact email draining, but no admin route or admin UI for listing `contact_messages`, reviewing failed/skipped messages, or responding from the admin.

Problem: The storefront can tell a customer their inquiry was accepted while the owner may have no normal admin place to see that message if notification email is unset, suppressed, failed, or not monitored.

Why it matters: Contact is not a side feature here. The site explicitly uses it for custom candles, gift questions, order support, returns, damaged items, and privacy/support requests.

Customer impact: A customer can ask about a custom candle, gift, delivery issue, or order problem and never receive a reply, while believing the business received the request.

Business impact: Lost custom/gift sales, missed support obligations, damaged trust, and avoidable reputation risk for a small family shop.

Admin impact, if applicable: The owner must depend on email configuration/logs/database access rather than a simple owner-facing queue or health state.

Recommended change: Add an admin-visible contact-message inbox/status view or an equivalent owner-facing recovery mechanism. At minimum, the admin should be able to see new, sent, failed, and suppressed contact messages; the dashboard should surface messages needing attention; and production setup should require or verify the owner notification recipient before launch.

Acceptance criteria: A submitted contact message is visible to the owner from an admin UI or other documented non-developer workflow even if the notification email is disabled or fails. Failed/suppressed contact notification states are visible and actionable. Launch configuration cannot silently accept contact messages while no owner recipient or owner-facing review path exists.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: This does not require a complex CRM. A simple admin inbox/status list is enough for this business.

### CND-015

Title: Gift-message workflow is split between checkout notes and the contact form

Status: OPEN

Priority: HIGH

Area: Gifting / Checkout / Admin Fulfillment

Page/Screen: FAQ; Checkout order notes; Contact form; Admin order detail

Evidence: Current FAQ data answers `Can I include a gift message?` with `Simply leave a note with your order and send your gift message through our Contact Form. We'll include it with your order.` Checkout already provides `Order Notes (optional)` with placeholder `Any special requests...`; the frontend sends `notes` with the order, `CreateOrderRequest` accepts `notes`, `order_service.py` stores `notes` on the order, and the admin order detail page displays `order.notes`. The contact form is a separate message path and is not attached to an order in the reviewed implementation.

Problem: The customer is told to use two different channels for one gift request: order notes and the contact form. The order-attached note exists, but the FAQ pushes the actual gift message into a separate inquiry that the owner must manually match.

Why it matters: Gift messages are operational details that belong with the order being packed. Splitting them creates exactly the kind of small manual mistake that embarrasses a family gift business.

Customer impact: A customer may believe their gift message is handled, but the message may be missed, unmatched, or handled too late.

Business impact: Missed gift notes, support complaints, lower gift confidence, and weaker conversion for occasions where presentation matters.

Admin impact, if applicable: The family must manually connect a contact-form message to an order, often without a required order number and with no reviewed admin contact-message inbox.

Recommended change: Make gift messages order-attached by default. Rename or guide the checkout field as `Gift message or order notes`, update the FAQ to match that single flow, and show the note clearly in the admin fulfillment/packing view. If the business wants gift-message review before purchase, require enough data to connect the contact message to an order or quote.

Acceptance criteria: A customer can add a gift message during checkout without using a separate contact form. The message is stored on the order and visible to the admin during fulfillment. FAQ/contact/checkout copy all describe the same flow. If contact-form gift requests remain supported, the admin has a reliable way to match them to an order.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: Related to CND-014. This is a workflow clarity issue, not a request for personalization software.

### CND-016

Title: Lavender Dream uses unrelated pet/document imagery instead of candle photography

Status: OPEN

Priority: BLOCKER

Area: Product Media / Merchandising / Trust

Page/Screen: Product Listing; Product Detail gallery

Evidence: Isolated desktop/mobile screenshots from a temporary copy of the current catalog show `lavender-dream-300ml` using an unrelated pet/outdoor photo as the primary product image. The PDP gallery thumbnails also include other non-product imagery, including a document/screenshot-like image and unrelated people/pet imagery. Database inspection shows four `product_images` rows for `lavender-dream-300ml`, with the unrelated pet photo marked primary through `is_primary=1`. The clean visual stack reported no route or console errors, so this is not a rendering fallback.

Problem: The only active product with gallery media is showing images that do not represent the candle being sold.

Why it matters: Product photography is a primary trust and conversion asset for candles. Wrong imagery is worse than missing imagery because it makes the shop look fake, careless, or compromised.

Customer impact: A customer cannot inspect the candle and may abandon immediately because the product page appears untrustworthy.

Business impact: Lower conversion, brand damage, and possible support/reputation issues if customers think the site is broken or scam-like.

Admin impact, if applicable: The admin workflow currently treats any uploaded image as publishable product media; there is no reviewed/approved media state visible in the launch process.

Recommended change: Remove the unrelated images from customer-facing product media and replace them with owner-approved candle photography before launch. Add a product media readiness/review step so active products cannot be considered launch-ready until images are accurate, approved, and product-specific.

Acceptance criteria: `lavender-dream-300ml` listing and PDP gallery show only accurate candle/product/packaging images. No active product displays unrelated pets, documents, people, or arbitrary uploads as product media. A launch checklist or admin readiness state records that product media has been reviewed by the owner.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: This is related to CND-002 but distinct. CND-002 covers missing photography; this covers misleading existing media.

### CND-017

Title: Customer order history hides payment state and payment recovery actions

Status: OPEN

Priority: HIGH

Area: Account / Orders / Payment Recovery

Page/Screen: My Orders; Order Detail

Evidence: `OrderResponse` exposes `payment_method` and `payment_status`. `order_service.py` creates card and bank-transfer orders with fulfillment `status = 'pending'` and `payment_status = 'pending'`, while COD orders use `payment_status = 'cod_pending'`. The customer order list in `frontend/app/[locale]/orders/page.tsx` renders only the short order ID, `OrderStatusBadge` from `order.status`, date, item count, and total. `OrderStatusBadge` translates fulfillment `pending` as `Pending`. The order list does not render `order.payment_status`, payment method, `Retry payment`, or a bank-transfer instruction cue. The order detail page does have a payment block and card retry link, but the account order list gives no visible signal that an order still needs customer payment action.

Problem: Unpaid card or bank-transfer orders can look like ordinary pending fulfillment orders in the customer's account.

Why it matters: Payment state is not secondary information when the customer still needs to act. If the customer misses a card redirect, payment fails, or a bank transfer is still pending, the account area should help recover the sale.

Customer impact: A returning customer may think the family is processing the order when the order is actually waiting for payment or retry.

Business impact: Delayed or lost payment, more unpaid orders, and avoidable follow-up from the family.

Admin impact, if applicable: The owner may need to manually chase customers for orders that the account page could have recovered.

Recommended change: Make the order list payment-aware. Show payment method/status on each order card, and surface direct actions or clear links for unpaid states: `Retry payment` for failed/pending card orders and `View bank transfer details` for pending bank-transfer orders. Keep fulfillment status separate from payment status.

Acceptance criteria: The customer order list clearly distinguishes fulfillment status from payment status for COD, card, and bank-transfer orders. Pending/failed card orders expose a visible retry action or direct recovery link from the list. Pending bank-transfer orders expose a visible transfer-details link or payment-instructions cue from the list. Automated coverage proves paid, COD-pending, card-failed/pending, and bank-transfer-pending order-card states.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: Related to CND-004, but distinct. CND-004 covers missing immediate confirmation instructions; this covers returning customer recovery from account order history.

### CND-018

Title: Free-shipping and fallback shipping rules are developer-only despite admin delivery settings

Status: OPEN

Priority: MEDIUM

Area: Admin Delivery / Shipping Pricing / Commercial Operations

Page/Screen: Admin Delivery; Checkout shipping summary; Site banner/promotions

Evidence: The admin delivery page only reads and saves four availability toggles: `speedy_office_enabled`, `speedy_door_enabled`, `econt_office_enabled`, and `econt_door_enabled`. `DeliverySettingsUpdate` contains only those four booleans, and the `delivery_settings` table stores only those four method switches plus `updated_at`. The actual commercial shipping rules live in code constants: `FREE_SHIPPING_THRESHOLD_CENTS = 5000`, `FALLBACK_SHIPPING_CENTS = 500`, `PACKAGING_WEIGHT_GRAMS = 200`, and `SHIPPING_CENTS_MAX = 3000` in `app/constants.py`, mirrored by `FREE_SHIPPING_THRESHOLD_CENTS = 5000` and `FALLBACK_SHIPPING_CENTS = 500` in `frontend/lib/constants.ts`. Checkout and `ShippingPriceSummary` use those constants to show the free-shipping threshold and calculate totals. Separately, the site banner is admin-managed free text; the seed banner advertises `Free shipping on orders over €50`, and the current database shows banner copy can be edited independently of shipping rules.

Problem: The owner can turn courier methods on/off, but cannot change the free-shipping threshold, fallback shipping amount, packaging weight buffer, or shipping maximum from the admin. Marketing/banner text can also drift from the actual checkout rule.

Why it matters: Shipping thresholds are commercial controls, not developer-only implementation details. A family candle business may need to adjust them when courier prices, margins, seasonal campaigns, or average order values change.

Customer impact: Customers can be shown a free-shipping promise or checkout nudge that no longer matches the business's intended offer if copy and hard-coded pricing rules drift.

Business impact: The family may give away margin with the wrong threshold, over/under-charge fallback delivery during courier outages, or need a developer for routine shipping policy changes.

Admin impact, if applicable: The admin delivery screen looks like the place to manage delivery, but it cannot manage the values that affect customer totals and promotions.

Recommended change: Make the free-shipping threshold and fallback shipping amount owner-manageable or expose them from one backend source of truth to both storefront and admin. If the business intentionally wants these fixed for launch, show the active values read-only in Admin Delivery and prevent/free-text-warn banner copy that advertises a conflicting threshold.

Acceptance criteria: Admin users can see the active free-shipping threshold and fallback shipping amount in Admin Delivery. Either those values are editable through an owner-approved workflow, or they are explicitly marked fixed and sourced from a single backend configuration. Storefront banner/checkout/cart messaging cannot advertise a different threshold from the rule used at checkout. Automated coverage proves frontend/backend threshold consistency.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: This is not a request for complex shipping tables. A small number of owner-visible commercial controls would be enough.

### CND-019

Title: Admin dashboard reports unpaid orders as weekly revenue

Status: OPEN

Priority: HIGH

Area: Admin Dashboard / Financial Reporting / Payment Operations

Page/Screen: Admin Dashboard

Evidence: `admin_service.get_dashboard_stats()` calculates `revenue_this_week_cents` as `SUM(total_cents)` for orders created in the last 7 days where `status != 'cancelled'`; it does not filter by `payment_status`. The admin dashboard renders that value under the label `Revenue This Week`. Current database evidence shows three non-cancelled orders in the last 7 days, all `payment_method = cod` and `payment_status = cod_pending`, totaling 12,835 cents; the same database query for paid weekly revenue returns 0 cents.

Problem: The dashboard can tell the owner they have weekly revenue when no payment has actually been collected.

Why it matters: Cash-on-delivery, bank transfer, and card payments have different payment states. A small business owner needs to know what is paid, what is awaiting payment, and what is only an order value.

Customer impact: Indirect. If the family believes orders are already revenue, payment follow-up and fulfillment decisions can become sloppy.

Business impact: Misleading cashflow, weaker payment reconciliation, and possible fulfillment of orders before payment handling is clear.

Admin impact, if applicable: The owner cannot trust the top dashboard revenue card without manually reconciling payment status elsewhere.

Recommended change: Separate paid revenue from open order value. Rename the current metric to `Open order value` if it intentionally includes unpaid orders, or calculate `Revenue This Week` only from `payment_status = 'paid'` plus any owner-approved COD rule after delivery. Surface pending/COD/bank-transfer amounts separately.

Acceptance criteria: Admin Dashboard distinguishes paid revenue from unpaid/open order value. COD pending, bank-transfer pending, and failed/pending card orders are not counted as paid revenue. Tests cover unpaid COD, pending bank transfer/card, paid orders, and cancelled orders.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: This matters even before card/bank-transfer launch because COD orders are currently represented with `payment_status = cod_pending` until delivery.

### CND-020

Title: Admin dashboard does not surface the daily work queue

Status: OPEN

Priority: HIGH

Area: Admin Dashboard / Owner Operations

Page/Screen: Admin Dashboard

Evidence: The backend dashboard response includes `orders.by_status` and `low_stock_count`, and the backend also exposes `GET /v1/admin/products/low-stock`. `frontend/lib/types.ts` defines `AdminStats` with only `orders_today`, `revenue_this_week_cents`, and `active_product_count`; `frontend/lib/api.ts` maps `/v1/admin/dashboard` down to only those three fields. `frontend/app/[locale]/admin/page.tsx` renders only three cards: Orders Today, Revenue This Week, and Active Products. Current database evidence has three `pending` orders and one `confirmed` order, but the dashboard UI does not show pending/confirmed/shipped/delivered counts, low-stock count, or direct links to the orders/products needing attention.

Problem: The dashboard is a performance summary, not an operational starting point. It hides the exact work the family needs to do today.

Why it matters: For a small candle business, the admin home page should answer: what orders need confirmation, payment attention, packing, shipping, delivery follow-up, or stock action?

Customer impact: Orders can sit in `pending` or `confirmed` longer because the owner has to remember to inspect other screens manually.

Business impact: Slower fulfillment, missed low-stock replenishment, and more avoidable owner/admin effort.

Admin impact, if applicable: A family member opening the dashboard cannot see the queue of work without navigating to other pages and filtering mentally.

Recommended change: Turn the dashboard into an operational queue. Surface counts and links for pending orders, confirmed/ready-to-ship orders, unpaid/payment-attention orders, low-stock products, and contact messages needing attention once CND-014 is fixed. Keep revenue/performance metrics secondary.

Acceptance criteria: Admin Dashboard shows actionable work cards or lists for orders by fulfillment status, payment attention, low-stock products, and contact messages needing attention. Each card links to the relevant filtered admin page. Backend response fields are carried through frontend types instead of being dropped. Tests cover visible pending/confirmed order counts and low-stock count.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: Related to CND-005, CND-014, and CND-019, but distinct: this is about what the owner sees first when opening admin.

### CND-021

Title: Atelier story page relies on 1x1 placeholder images instead of real atelier photography

Status: OPEN

Priority: HIGH

Area: Atelier / About / Trust / Family Story

Page/Screen: Atelier / About; Admin Atelier content

Evidence: The current `about_sections` and `about_items` database rows have `image_id` empty for every published section/item. `frontend/components/atelier/AtelierSections.tsx` therefore falls back to hard-coded files such as `/static/products/lavender-dreams-300ml.webp`, `/static/products/midnight-amber-300ml.webp`, and `/static/products/vanilla-bourbon-300ml.webp`. Local file inspection shows all three fallback files are WebP images with dimensions `1x1`. The public hero, text-image, and collections sections stretch these images with `object-cover`, including the full-viewport Atelier hero.

Problem: The page that should prove the craft, family identity, and atelier story is visually backed by stretched one-pixel placeholder files.

Why it matters: For an unknown family candle business, the Atelier page is a trust page. It should show real making, materials, packaging, hands, workshop, or finished products, not invisible placeholders.

Customer impact: A customer looking for proof that the shop is real and handmade sees a polished layout with no meaningful visual evidence behind the story.

Business impact: Weaker trust, weaker family/craft positioning, and a cheaper unfinished impression of the brand.

Admin impact, if applicable: The admin editor allows image upload/clear, but the current published content has no image readiness warning. Clearing an image silently falls back to the 1x1 static placeholders.

Recommended change: Replace the static fallback placeholders with real owner-approved atelier/product/story imagery before launch, and add an admin readiness cue for published visual sections without a real image. If a section can launch without an image, use an intentional design state rather than a stretched placeholder image.

Acceptance criteria: No published Atelier section renders a 1x1 placeholder image. Hero, story, atelier, process, and collection sections either show real approved photography/imagery or an intentional no-image layout. Admin users can identify published sections/items missing real imagery before launch.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: This is separate from product photography findings. It concerns the brand/trust story page and the admin-managed content state behind it.

### CND-022

Title: Atelier copy does not establish the real family, makers, or place behind the candles

Status: OPEN

Priority: HIGH

Area: Atelier / About / Trust / Brand Story

Page/Screen: Atelier / About

Evidence: Current published Atelier copy uses generic phrases such as `our atelier`, `our hands`, `crafted slowly`, `luxury fragrance`, and `handmade design`, but does not identify who makes the candles, where they are made beyond a generic atelier, why this family started the business, or any concrete owner/maker detail. The known business context is a family-owned candle production business, and the About page is the primary place customers would look for that proof.

Problem: The page says the candles are handmade, but it does not make the family business feel real or specific.

Why it matters: A small candle shop cannot rely only on generic luxury wording. Customers who have never heard of the brand need human, concrete trust signals that distinguish it from a template storefront.

Customer impact: The customer learns the brand wants to feel elegant, but not who is behind it, where the work happens, or why they should trust this family with an order or gift.

Business impact: Weaker differentiation, weaker trust, and less emotional connection for gift and repeat-purchase customers.

Admin impact, if applicable: The content is editable, but the current seed/live copy does not guide the owner toward the concrete business facts customers need.

Recommended change: Rewrite the Atelier story with owner-approved specifics: who the makers/family are, where production happens at an appropriate level of detail, why the business exists, what materials/processes are genuinely distinctive, and what customers can expect from a handmade order. Keep it concise and commercially useful.

Acceptance criteria: The Atelier page clearly answers who makes the candles, where/how they are made, what makes the family business credible, and why the products are different from generic alternatives. English and Bulgarian copy are both owner-approved and avoid placeholder/generic luxury claims.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: This does not require oversharing private family details. It requires enough authentic detail for a small unknown shop to feel real.

### CND-023

Title: Admin Atelier and FAQ editors publish newly created content live by default

Status: OPEN

Priority: MEDIUM

Area: Admin Content / Publishing Safety

Page/Screen: Admin Atelier; Admin FAQ

Evidence: `CreateAboutItemRequest.is_published` defaults to `True`, `about_service.create_item(...)` inserts new about items with `is_published = 1` unless explicitly overridden, and `AtelierAdminManager` creates new items without exposing a draft/hidden choice in the new-item form. `faq_service.create_item(...)` always inserts new FAQ items with `is_published = 1`, and `FaqManager` validates only English question/answer before creating the item. Existing published sections render newly created items immediately on the public Atelier or FAQ pages.

Problem: A family member adding or testing new content can accidentally publish unfinished FAQ or Atelier content before it has been reviewed, translated, imaged, or checked in the public layout.

Why it matters: Content admin should reduce developer dependence without creating a new way to make the live shop look unfinished.

Customer impact: Customers may see incomplete FAQ answers, English-only Bulgarian fallback content, unfinished collection cards, or content that has not been checked in context.

Business impact: Avoidable trust damage and cleanup work from simple content edits.

Admin impact, if applicable: The owner has to create first and hide afterward, rather than composing safely and publishing when ready.

Recommended change: Create new admin-managed Atelier and FAQ items as hidden/draft by default, or expose a clear `Create hidden` / `Publish now` choice. Add a lightweight preview or public-view link so the owner can check formatting before publishing. Keep the workflow simple; this does not need a complex CMS.

Acceptance criteria: New FAQ and Atelier items are not publicly visible until the admin intentionally publishes them, or the admin must explicitly choose live publishing. The editor clearly shows published/hidden state before and after saving. A non-technical owner can preview or verify public rendering before making a new item live.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: Current seeded Bulgarian content is complete for the reviewed rows; the risk is the live-by-default publishing workflow for future owner edits.

### CND-024

Title: Checkout delivery fields are not programmatically labelled

Status: OPEN

Priority: HIGH

Area: Checkout / Accessibility / Conversion

Page/Screen: Checkout delivery section

Evidence: An isolated checkout browser pass against a temporary copy of the current catalog captured `checkout-initial-mobile-390.png`, `checkout-door-ready-mobile-390.png`, and `checkout-office-ready-desktop-1440.png`. The live DOM for six door-delivery text/tel inputs reported no `id`, no `aria-label`, no `aria-labelledby`, and `labels=[]`, while visual labels such as `Postal code *`, `Street and number *`, and `Phone for courier *` were visible nearby. Chrome's accessibility tree named the delivery fields from placeholders/current values such as `e.g., Sofia`, `1000`, `e.g., Vitosha Blvd 100`, `e.g., A`, `e.g., 12`, and `+359...`. The desktop office-pickup phone field had the same issue. The main checkout email/name fields were correctly labelled, so the defect is localized to `DeliverySection` subcomponents.

Problem: The form looks labelled but is not labelled correctly for assistive technology or voice-input users.

Why it matters: Delivery details are mandatory checkout fields. If a customer cannot identify city, postcode, street, or courier phone reliably, checkout becomes inaccessible at the point of purchase.

Customer impact: Screen-reader and voice-input customers may hear example text instead of the actual field purpose, increasing errors or preventing completion.

Business impact: Accessibility defects in checkout directly reduce addressable conversion and create legal/compliance risk.

Admin impact, if applicable: Not applicable.

Recommended change: Give every delivery field a stable `id` and pair the visible `<label>` with `htmlFor`, or use equivalent `aria-labelledby` when the component structure requires it. Keep placeholders as examples only. Include error text through `aria-describedby` where validation messages appear.

Acceptance criteria: Every delivery input in office and door checkout states can be found by its visible label in automated tests. Chrome accessibility tree names match the visible labels, not placeholder examples. The fix covers city typeaheads, office search/filter, postcode, street, building, apartment, and phone fields without weakening the visual design.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: Related QA bug: QA-040. This is separate from backend delivery validation defects; it concerns whether customers can operate the checkout form accessibly.

### CND-025

Title: Mobile checkout places the submit action before the final order summary

Status: OPEN

Priority: HIGH

Area: Checkout / Mobile Conversion / Order Review

Page/Screen: Mobile Checkout

Evidence: The retained mobile checkout screenshot `checkout-door-ready-mobile-390.png` shows the `Place Order` button and legal text before the `Order Summary` card and final `Total` row. Browser layout metrics for the same state reported viewport height `844`, visible `Place Order` button `top=731`, and `Order Summary` heading `top=924`, below the fold. In `frontend/app/[locale]/checkout/page.tsx`, the mobile-only submit button is rendered inside the form before the sibling `<aside>` that contains the order summary, so mobile stacking naturally puts the action before the final review block.

Problem: Mobile customers reach the primary submit action before the page presents the final order summary and payable total in the natural flow.

Why it matters: A checkout should make the customer confident about what they are buying and paying before asking them to place the order. This is especially important on mobile, where the visible viewport is limited and most purchase hesitation happens.

Customer impact: Customers can submit without naturally reviewing the final subtotal, shipping, and total, or they may tap back/scroll around to verify the total, adding friction.

Business impact: Lower trust at the highest-intent step, more hesitation, and more post-order questions about totals or shipping.

Admin impact, if applicable: Not applicable.

Recommended change: On mobile, place the order summary and final total before the primary `Place Order` button, or move the mobile submit action into the summary card after the total. Keep the legal disclosure adjacent to the submit action, but ensure the total is visible before the action.

Acceptance criteria: At mobile widths, the final payable total appears before or in the same block as the primary `Place Order` action. A screenshot or browser layout test confirms `Order Summary`/`Total` precedes the visible submit button. Desktop sticky summary behavior remains intact.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: Related QA bug: QA-041. This is separate from CND-012, which tracks missing product thumbnails in the cart/checkout summary.

### CND-026

Title: Admin Atelier and FAQ editors are unmanageably long on mobile because every item is expanded

Status: OPEN

Priority: MEDIUM

Area: Admin Content / Mobile Admin Usability

Page/Screen: Admin Atelier; Admin FAQ

Evidence: Retained screenshots from an isolated browser pass show `admin-atelier-mobile-390.png` with a document height of 27,202px and `admin-faq-mobile-390.png` with a document height of 19,322px. The desktop screenshots also show every section/item expanded in one long page. `AtelierAdminManager` maps every about section and every item directly into full edit forms, and `FaqManager` maps every FAQ section and item into full editable question/answer forms. There is no collapse, search, section jump, section summary, or focused edit mode in the reviewed UI.

Problem: The owner has to scroll through a huge wall of bilingual fields to find or edit one FAQ answer, story section, collection card, or process step.

Why it matters: Content management is supposed to let a non-technical family member update the site without developer help. If the editor is physically hard to navigate, routine content changes become risky and frustrating.

Customer impact: Indirect. Stale or incorrect FAQ/story content is less likely to be fixed promptly if the admin screen is uncomfortable to use.

Business impact: More developer dependence, slower content corrections, and higher chance of editing the wrong item.

Admin impact, if applicable: A family member working from a phone or small laptop must scroll through 19k-27k pixels of expanded forms and repeated controls to make a small change.

Recommended change: Make admin content editors navigable. Collapse sections/items by default or show compact summaries with explicit edit buttons. Add section anchors, a sticky section list, or a simple filter/search. Preserve the current straightforward fields, but avoid rendering every full form expanded at once.

Acceptance criteria: On mobile and desktop, an admin can jump to or open a specific FAQ/Atelier section without scrolling through every preceding full form. Existing items show compact status/summary until selected for editing. Screenshots prove the mobile page is usable for targeted edits and does not require scanning a 19k-27kpx expanded form stack.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: This is a usability/operations issue, not a request for a complex CMS.

### CND-027

Title: Admin Atelier and FAQ delete actions permanently remove content without confirmation or undo

Status: OPEN

Priority: MEDIUM

Area: Admin Content / Destructive Actions / Operations Safety

Page/Screen: Admin Atelier; Admin FAQ

Evidence: `AtelierAdminManager` wires the item `Delete` button directly to `deleteAboutItem(section.slug, item.id)` through `run(...)`, and `FaqManager.removeItem(...)` calls `deleteFaqItem(itemId)` directly. The backend services hard-delete rows with `DELETE FROM about_items` and `DELETE FROM faq_items`. The reviewed UI shows `Delete` / `Delete item` buttons beside repeated content items, but no confirmation dialog, typed confirmation, undo, archive/restore state, or soft-delete recovery path was found in the reviewed implementation.

Problem: A single mistaken click can permanently remove public FAQ/story content.

Why it matters: A non-technical owner should be able to manage content without fear that one slip destroys useful copy or public information.

Customer impact: Public FAQ answers, collection cards, process steps, or story details can disappear until somebody notices and recreates them.

Business impact: Avoidable content loss, weaker customer support information, and extra recovery work.

Admin impact, if applicable: The family has no obvious recovery path after an accidental delete other than manually recreating the content or asking a developer to restore from a backup.

Recommended change: Add a confirmation step for destructive content deletes and provide either undo, soft-delete/archive, or a clear recovery path. At minimum, require confirmation that names the item being deleted and keep non-destructive hide/unpublish as the safer default action.

Acceptance criteria: Clicking delete on an Atelier or FAQ item does not immediately hard-delete it. The admin must confirm the destructive action, the confirmation names the affected item, and accidental deletion can be recovered through undo/restore or a documented owner-accessible recovery path. Tests cover cancel and confirm paths.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: Hide/unpublish already exists for many items and should be the lower-risk default for routine content removal.

### CND-028

Title: Admin Products CSV import reference is API-only and uses stale taxonomy guidance

Status: OPEN

Priority: MEDIUM

Area: Admin Products / Catalog Operations / Bulk Import

Page/Screen: Admin Products CSV Import Format Reference

Evidence: Retained screenshot `admin-products-csv-open-desktop-1440.png` shows an owner-facing `CSV Import Format Reference` panel that says products can be bulk imported via `POST /v1/admin/products/import`. The same panel lists `category` and `stock` under `Required columns` and gives example `category` values `Floral` and `Woody`. `frontend/app/[locale]/admin/products/page.tsx` renders that exact reference. The backend import code defines required headers as `id`, `name_en` or legacy `name`, and `price_cents`; `category` and `stock` are optional. The backend route docstring says taxonomy fields use managed slugs, not free text. Current taxonomy data has category slugs `small`, `medium`, and `premium`, while `floral` and `woody` are label slugs, not category slugs. The reviewed admin page shows no actual file-upload control for this import, only the API endpoint reference.

Problem: The admin UI gives a non-technical owner a technical endpoint and a sample CSV that does not match the current import contract or taxonomy model.

Why it matters: Bulk import is where one mistake can damage many products at once. If the family follows the visible example, rows can fail with taxonomy errors or put scent-family terms into the wrong field.

Customer impact: Imported products may end up with wrong or missing browsing taxonomy, making scents, sizes, collections, or gift paths harder to find.

Business impact: Seasonal launches and larger catalog updates become slower, riskier, and more dependent on developer help.

Admin impact, if applicable: The owner cannot confidently prepare or run an import from the admin screen. They are told to use an API endpoint, false required fields, and category examples that no longer fit the current taxonomy.

Recommended change: Either remove this reference from the owner-facing admin UI if CSV import is developer-only, or make it owner-safe. Provide an actual upload flow or clearly marked template download, list the real required and optional columns, explain that taxonomy values are slugs, and show examples such as `product_type=candles`, `category=medium`, and `labels=floral,woody` according to the final taxonomy model.

Acceptance criteria: The visible CSV reference matches the backend import contract. `category` and `stock` are not falsely listed as required. Examples use valid active taxonomy slugs and distinguish category/type/labels. The owner can either import from the admin UI with clear validation errors or the API-only reference is removed from normal owner-facing admin screens. Automated or manual test evidence proves the documented example imports successfully.

Date discovered: 2026-07-31

Last reviewed: 2026-07-31

Notes: This is not a request for a complex stock system or ERP integration. A small accurate template, or hiding developer-only import notes from the owner UI, is enough.

## Open Questions

- Is the current `atelier_marie.db` catalog intended to represent launch data, staging data, or disposable sample data?
- What products are actually sold at launch?
- Who normally buys them?
- What makes these candles different from alternatives?
- Are they handmade, and where are they produced?
- Which products are bestsellers?
- Are products held in stock, made to order, or both?
- Are personalised candles, gift sets, or corporate/bulk orders offered at launch?
- Who monitors contact form messages, and what should happen if the owner notification email fails?
- Should gift messages be entered only during checkout, or should pre-order gift/custom requests stay in the contact flow?
- Where does the company ship?
- Which payment methods are actually supported at launch?
- If bank transfer is supported, who will mark payments received and how often?
- How long should unpaid card or bank-transfer orders remain open before the family follows up or cancels them?
- Which courier or couriers are actually used for fulfillment at launch?
- Are the EUR 50 free-shipping threshold and EUR 5 fallback shipping amount fixed launch policy, or should the owner manage them without a developer?
- What delivery expectations exist?
- How are returns, refunds, cancellations, and damaged products handled operationally?
- How much can the family realistically manage operationally?
- Should admin dashboard revenue mean paid revenue only, or should open order value be shown as a separate metric?
- Which daily admin queues should the family see first: pending orders, unpaid orders, ready-to-ship orders, low stock, contact messages, or all of them?
- Which family/maker/place details can be safely shown on the Atelier page?
- Are the current 1x1 Atelier fallback images intentional placeholders, and should published sections be blocked or warned when no real image is present?
- Should new admin-managed Atelier/FAQ content default to hidden/draft until explicitly published?
- Should Admin Atelier/FAQ editors default to collapsed summaries, focused edit mode, or another simple navigation model?
- Should admin content deletion be soft-delete with restore, immediate undo, or confirmed hard-delete with documented backup recovery?
- Should CSV product import be a normal owner-facing admin feature, or should it be developer-only and removed from the visible admin UI?
- What page, flow, screenshot, or implementation should be reviewed next?
- Are the current Lavender Dream images accidental test uploads, and should they be removed from the shared catalog database now or preserved until replacement photos are ready?

## Review History

### 2026-07-31

- Created review tracking files.
- Reviewed current repository and database evidence for business context, product media completeness, taxonomy/merchandising, and legal identity.
- Recorded CND-001, CND-002, and CND-003.
- Reviewed checkout/payment confirmation evidence and recorded CND-004.
- Reviewed admin order/payment/shipping evidence and recorded CND-005 and CND-006.
- Reviewed admin product create/edit implementation and recorded CND-007.
- Reviewed product listing/detail implementation, public taxonomy data, product content fields, and FAQ content; recorded CND-008 and CND-009.
- Reviewed cart drawer, cart context, cart API types, backend cart availability handling, checkout cart usage, and current stock data; recorded CND-010 through CND-013.
- Reproduced cart drawer mobile states in-browser with retained screenshots; confirmed stale unavailable items are hidden, stock-limit increments remain enabled, line thumbnails are absent, and free-shipping threshold messaging is missing in the live drawer.
- Reviewed contact/gift-message operations and recorded CND-014 and CND-015.
- Reviewed desktop/mobile product listing and PDP screenshots plus product media database/static files; recorded CND-016.
- Reviewed account page, customer order history, order detail, payment status rendering, and retry-payment path; recorded CND-017.
- Reviewed Admin Delivery settings, delivery settings API/model/table, checkout shipping-threshold constants, fallback shipping constants, and managed banner independence; recorded CND-018.
- Reviewed Admin Dashboard UI/API/service, current order/payment data, low-stock support, and frontend stats mapping; recorded CND-019 and CND-020.
- Reviewed contact form persistence/notification handling, absence of an admin contact-message view, FAQ gift-message copy, checkout notes, and admin order-note display; recorded CND-014 and CND-015.
- Reviewed Admin Atelier/FAQ content management, public Atelier rendering, current about/FAQ database content, static fallback image files, and live-by-default content creation; recorded CND-021 through CND-023.
- Reviewed checkout visual/mobile delivery states with retained screenshots and live DOM/accessibility-tree evidence; recorded CND-024.
- Reviewed mobile checkout order-summary placement in the same screenshot/layout pass; recorded CND-025.
- Reviewed public Atelier/FAQ and Admin Atelier/FAQ desktop/mobile screenshots from an isolated full-stack run; recorded CND-026 and CND-027 for admin content editor usability and destructive delete safety.
- Reviewed Admin Products desktop/mobile list, create, edit, media, and CSV-reference screenshots from an isolated full-stack run; updated CND-002 and CND-007 with admin visual evidence and recorded CND-028 for stale/API-only CSV import guidance.
