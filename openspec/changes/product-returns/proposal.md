# Product Returns - Proposal

## Motivation

AtelierMarie can take an order all the way to `delivered`, but once a candle is in
the customer's hands there is no path back. If a customer receives a broken jar, the
wrong scent, or simply changes their mind, the owner has no in-app way to accept the
item back, restore stock, or reconcile the refund against the original payment. Today
that happens over email and the Stripe Dashboard, with nothing tying it to the order.

This change adds a full return lifecycle (RMA): a customer requests a return for
specific delivered items, the owner approves or rejects it, marks the goods received,
and issues a refund. Card refunds are executed automatically through the Stripe
Refunds API; bank-transfer and pay-on-delivery refunds are recorded in-app while the
owner settles them out of band. Returns and refunds become first-class, auditable
records aligned with order and payment state — no more manual cross-checking.

This change **supersedes** the deferred `openspec/changes/deferred/stripe-refunds/`
proposal: automated Stripe refunds are delivered here as the refund-execution half of
the return flow, rather than as a standalone admin action.

## Scope

### Capabilities

1. **Return requests (RMA)** — a customer requests a return against a delivered order,
   selecting specific line items and quantities, with a reason. One open request per
   order at a time.
2. **Return eligibility window** — returns are allowed only for `delivered` orders
   within a configurable window (default 14 days from delivery). Requested quantities
   are capped at ordered-minus-already-returned per line item.
3. **Return state machine** — `requested → approved → received → refunded`, with
   `rejected` and `cancelled` terminal branches. Owner-driven, auditable, separate
   from the order fulfillment status.
4. **Stock restoration on receipt** — approved items restore product stock when the
   owner marks them received (not on request, not on refund).
5. **Refund execution and tracking** — card orders refund automatically via the Stripe
   Refunds API (partial or full, by returned amount); bank-transfer and COD orders get
   a recorded manual refund the owner settles externally. Refund amount, status, and
   provider references are stored and confirmed via webhook for cards.
6. **Return audit timeline** — append-only `return_events` capturing every transition,
   admin note, refund attempt, and Stripe refund webhook.
7. **Admin return operations** — a returns queue, per-return detail with the item
   breakdown and refund state, and the approve/reject/receive/refund actions (each
   requiring an admin note where it changes money or state).
8. **Customer return UX** — request a return from a delivered order, see request status
   and refund progress in order history/detail.
9. **Return notification emails** — customer emails on return approved, rejected, and
   refunded; admin alert on a new return request.

### New Capabilities
- `product-returns`: Return-request lifecycle, per-item eligibility, refund execution
  (auto Stripe + manual others), return audit, admin queue, and customer UX.

### Modified Capabilities
- `order-management`: `delivered` orders expose returnable line items; order detail
  reports returned quantities per item and any linked return/refund state. `delivered`
  remains terminal for fulfillment — returns do not reopen the order status.
- `admin-orders`: order detail surfaces linked returns and a "Start return" action;
  dashboard revenue is reduced by confirmed refund amounts.
- `product-service`: stock restoration gains a return-receipt entry point (mirrors the
  cancellation restore path).
- `email-service` / `email-templates`: three new customer events
  (`return_approved`, `return_rejected`, `return_refunded`) and one admin event
  (`admin_return_requested`), each with `en`/`bg` plain-text templates.

## Non-Goals

- **Exchanges / store credit.** Returns produce a refund only. Swapping for a different
  scent is out of scope.
- **Customer-initiated cancellation of an in-flight return.** The customer may cancel a
  request only while it is still `requested`; after approval it is owner-driven.
- **Return shipping labels / courier pickup.** No courier API integration for return
  legs. The owner arranges physical return out of band; the app tracks state only.
- **Refunding shipping.** Shipping is paid by the customer to receive the goods and is
  never refunded. Refunds cover returned item value only (item snapshot price ×
  quantity), whether partial or full-order.
- **Partial-line refund overrides.** Refund amount is derived from returned items at
  their `order_items` snapshot price. The owner cannot type an arbitrary refund figure
  in this change (restocking fees, goodwill credits deferred).
- **Automated bank-transfer / COD refunds.** Only Stripe card refunds are executed by
  the app. Bank and cash refunds are recorded, then settled by the owner externally.
- **Reversing a refund.** Once `refunded`, the return is terminal. Corrections happen in
  Stripe/bank plus a manual order note.

## Technical Approach

- Keep SQLite as the Layer 1 system of record. Add `returns`, `return_items`, and
  append-only `return_events` tables. No Layer 2 involvement.
- Reuse the existing `payments` / `payment_events` and Stripe client wrapper from
  `payment-integration` for card refunds; store the Stripe refund id and confirm state
  from a `charge.refunded` / `refund.updated` webhook (idempotent by event id).
- Return refund amounts are computed server-side from `order_items.price_cents`
  snapshots × returned quantity — never trusted from the client.
- Stock restore reuses the same guarded `UPDATE products SET stock = stock + ?` path as
  order cancellation, invoked at `received`.
- New env/config constant `RETURN_WINDOW_DAYS` (default 14). Return status is separate
  from `orders.status`; `delivered` stays terminal.

## Impact

- **Backend:** new `app/services/return_service.py`, new `app/routes/returns.py`
  (customer) + admin return routes, `app/models/returns.py`, three new tables + indexes
  in `database.py`, refund execution wired through the existing Stripe wrapper, new
  Stripe refund webhook events handled in `webhook_service.py`.
- **Frontend:** customer "Request return" flow on delivered orders + return status in
  order history/detail; admin returns queue, return detail, and action modals.
- **Email:** four new events + `en`/`bg` templates.
- **Config:** `RETURN_WINDOW_DAYS` (default 14). No new secrets — reuses existing Stripe
  credentials.
- **Supersedes:** `deferred/stripe-refunds` — that proposal is annotated as superseded.
- **Revenue:** dashboard revenue must subtract confirmed refunds (net revenue).

## Resolved Decisions

- **Return window anchor:** measured from a dedicated `delivered_at` column on `orders`,
  added and backfilled by this change (see `order-management` delta). Not `updated_at`.
- **Shipping refund:** never refunded — customer pays shipping to receive the goods.
- **COD/bank refund:** always a manual outbound settlement recorded by the owner
  (single `refund_method` + optional `refund_reference`), performed only after the
  candle is received and inspected (`received → refunded`).
- **Stripe terminal error codes:** classify on the allowlist `charge_already_refunded`,
  `charge_disputed`, charge-not-refundable/expired (default all others to transient);
  exact codes verified against Stripe's API-error / Refund `failure_reason` docs at
  build (design Decision 14).
- **Re-request after rejection:** allowed — a customer may open a new return once the
  prior one is `rejected`/`cancelled`; only one *open* return per order at a time
  (product-returns spec, "Only one open return per order").

## Open Questions (Draft)

- Stripe refund destination when the original PaymentIntent is very old — confirm
  refund-to-original-payment-method still succeeds within Stripe's refund window (this
  is the transient-vs-terminal boundary case Decision 14 guards).
