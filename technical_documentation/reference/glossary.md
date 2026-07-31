# Glossary

Short definitions for project terms.

## Core Terms

`Layer 1`
: The production shop. Products, cart, checkout, orders, auth, admin, shipping, payments, email, legal, content. Must work reliably.

`Layer 2`
: Optional analytics/ML sandbox. Useful, but never required for sales.

`session_id`
: Anonymous browser identity. The cart is keyed to this.

`user_id`
: Logged-in user identity from Google OAuth.

`admin`
: A user/API caller allowed to use admin endpoints. Frontend guards are convenience only; backend checks matter.

`locale`
: Current language, `en` or `bg`.

## Product Terms

`price_cents`
: Base price in integer cents.

`effective_price_cents`
: Price after active discount. This is what checkout snapshots.

`taxonomy`
: Managed product type/category/label data. Not hardcoded frontend categories.

`primary image`
: The image used for cards and the main gallery image.

`zoom_url`
: High-resolution product image derivative used by lightbox/zoom.

`crop editor`
: Admin image tool that bakes crop, rotate, and zoom into the uploaded pixels.

`lightbox`
: Fullscreen product media viewer. Current product gallery uses one shared viewer for images and video.

## Cart And Order Terms

`cart item`
: Session-keyed product + quantity before checkout.

`order item`
: Immutable purchase snapshot. Keep historical name/price even if product changes later.

`items_total_cents`
: Sum of order item price snapshots times quantity.

`shipping_cents`
: Shipping charge snapshot.

`total_cents`
: `items_total_cents + shipping_cents`.

## Order Status

`pending`
: Order created, owner has not confirmed fulfillment yet.

`confirmed`
: Owner/admin accepted the order.

`shipped`
: Order has tracking/waybill and left fulfillment.

`delivered`
: Delivery complete.

`cancelled`
: Order cancelled. No later transitions.

## Payment Method

`cod`
: Cash/pay on delivery. Current default.

`card`
: Stripe Checkout card payment.

`bank_transfer`
: Manual bank transfer with IBAN instructions.

## Payment Status

`cod_pending`
: COD order waiting for delivery collection.

`pending`
: Card or bank transfer payment not paid yet.

`paid`
: Payment confirmed/collected.

`failed`
: Card payment/session failed or expired.

`refunded`
: Refund state. Refund automation is not the main MVP path.

## Shipping Terms

`office delivery`
: Customer chooses courier office/locker.

`door delivery`
: Customer enters a structured address.

`quote provenance`
: Whether shipping price came from live courier API, table, or flat fallback.

`fallback quote`
: Safe quote used when live courier pricing fails.

`waybill`
: Courier shipment record/tracking number, especially Speedy.

## Email Terms

`outbox`
: Database-backed queue of email send intents.

`placed email`
: Main order received email. Do not send before card/bank payment is actually confirmed.

`payment_pending email`
: Email that tells customer payment is still needed or pending.

`suppression`
: Do-not-email record after bounce/complaint.

## Analytics Terms

`consent-gated`
: Tracking only after user consent.

`JSONL`
: Event log file with one JSON object per line.

`DuckDB`
: Separate analytics reporting database. Not the shop source of truth.

`purchase_confirmed`
: Backend analytics event recorded from successful order creation. Optional, not a checkout dependency.
