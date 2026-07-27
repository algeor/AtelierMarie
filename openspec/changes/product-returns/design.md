# Product Returns - Design

## Goals / Non-Goals

**Goals:**
- Let a customer request a return for specific delivered items and quantities.
- Give the owner a controlled approve → receive → refund workflow, fully audited.
- Execute Stripe card refunds automatically; record bank/COD refunds for manual
  settlement.
- Restore stock exactly once, when returned goods are physically received.
- Keep return state separate from order fulfillment state; `delivered` stays terminal.
- Compute refund amounts server-side from immutable order snapshots.

**Non-Goals:**
- Exchanges, store credit, restocking fees, arbitrary refund amounts, return shipping
  labels, courier pickup, automated bank/COD refunds, or refund reversal.

## Decisions

### 1. Return state is separate from order fulfillment state

`orders.status` remains the fulfillment lifecycle and `delivered` stays **terminal** —
a return does NOT transition the order back to any active status. The return has its
own status on the `returns` row:

- `requested` — customer submitted; awaiting owner review
- `approved` — owner accepted; awaiting physical receipt
- `received` — goods received; stock restored; awaiting/attempting refund
- `refunded` — refund confirmed (Stripe) or recorded (manual); terminal
- `rejected` — owner declined; terminal
- `cancelled` — customer withdrew while still `requested`; terminal

Transitions:
- `requested → approved | rejected | cancelled`
- `approved → received`  (owner marks goods received) `| rejected` (owner can still
  decline if goods never arrive / arrive damaged beyond the claim)
- `received → refunded`
- `refunded`, `rejected`, `cancelled` are terminal.

Any transition outside this table SHALL be rejected with HTTP 422, matching the order
state-machine convention.

### 2. Data model: returns + return_items + return_events

`returns` — one row per return request:
- `id` (UUID text), `order_id` (FK), `session_id`, `user_id` (nullable — for
  cross-session ownership, mirrors orders)
- `status` (see Decision 1)
- `reason_code` (`damaged`, `wrong_item`, `not_as_described`, `changed_mind`, `other`)
- `reason_text` (sanitized free text, nullable)
- `refund_amount_cents` (computed at request time from item snapshots; re-verified at
  refund time)
- `refund_method` (`stripe` | `bank_transfer` | `cod_manual`) — derived from the order's
  `payment_method`
- `refund_status` (`none` | `pending` | `refunded` | `failed` | `manual_required`) —
  `manual_required` means an automated Stripe refund hit a terminal error and the owner
  must settle manually (see Decision 14)
- `stripe_refund_id` (nullable)
- `refund_reference` (nullable free text for manual bank/cash settlement note)
- `created_at`, `updated_at`, `received_at` (nullable), `refunded_at` (nullable)

`return_items` — the per-line breakdown:
- `id`, `return_id` (FK), `order_item_id` (FK to the exact snapshot line),
  `product_id`, `quantity` (units being returned), `price_cents` (copied from the
  `order_items` snapshot — the refund basis)

`return_events` — append-only audit (mirrors `payment_events`):
- `id`, `return_id`, `event_type` (`requested`, `approved`, `rejected`, `received`,
  `refund_attempted`, `refund_confirmed`, `refund_failed`, `cancelled`), `actor`
  (`customer` | `admin` | `system`), `admin_note` (nullable), `metadata` (nullable
  JSON — e.g. Stripe refund id / error), `created_at`.

Indexes: `returns(order_id)`, `returns(status)`, `returns(session_id)`,
`returns(user_id)`, `returns(stripe_refund_id)`, `return_events(return_id)`.

### 3. Eligibility: delivered orders, within the return window, per-item quantity cap

A return may be requested only when:
1. `orders.status == 'delivered'`, AND
2. now is within `RETURN_WINDOW_DAYS` (default **14**) of the delivery timestamp, AND
3. the order has **no open return** (`requested`/`approved`/`received`) — one open
   return at a time. After a `rejected`/`cancelled` return, a new request is allowed;
   after `refunded`, only remaining un-returned quantity is eligible.

Per line item, the requestable quantity is
`ordered_quantity − sum(quantity in prior non-rejected/non-cancelled returns for that
order_item)`. Requesting more than remaining → HTTP 422.

> **Load-bearing assumption (see Decision 15):** the per-item remaining-quantity cap has
> no single-column DB constraint backing it — it is a sum across sibling `return_items`.
> Its concurrency safety depends on the "one open return per order" invariant above: with
> at most one open return per order, no second return can concurrently accumulate quantity
> against the same `order_item`. If that invariant is ever relaxed (e.g. multiple
> concurrent partial returns), this cap loses its backstop and needs its own guard.

The window is measured from a dedicated `delivered_at` timestamp on `orders`, added by
this change (see the `order-management` delta). It is stamped when `update_status`
transitions an order to `delivered` and never changes afterward, so later edits cannot
move the window. Legacy delivered orders are backfilled once from their delivered
transition time, falling back to `updated_at` only for rows with no better source.

### 4. Refund amount is derived server-side from order snapshots

`refund_amount_cents = Σ (return_items.price_cents × return_items.quantity)`.

`price_cents` is copied from the immutable `order_items` snapshot at request time (the
discounted price actually charged — consistent with checkout). **Shipping is never
refunded.** The customer paid shipping to receive the goods; that cost is not reversed
on a return, whether partial or full-order. Refunds cover returned item value only. The
client never supplies an amount. The amount is re-verified at refund execution against
the stored `return_items` before any money moves.

### 5. Stock is restored on receipt-and-inspection, exactly once

The `received` transition means the owner has physically received the returned candle
**and inspected it** — it is the owner's confirmation that the goods are back and
acceptable. Refunds are only reachable from `received`, so money never moves before the
owner has the item in hand and has looked at it. If an inspection fails (item never
arrived, or arrived damaged beyond the claim), the owner uses `approved → rejected`
instead of `received`, and no stock is restored and no refund occurs.

Stock is restored at `received`, not at request (goods not back yet) and not at refund
(decouples money from inventory). Restoration reuses the guarded path from order
cancellation: `UPDATE products SET stock = stock + ? WHERE id = ?`, per `return_item`,
with a `rowcount == 0` warning log for deleted products. The `received` transition and
the stock restore happen in one transaction; `received_at` is stamped. Because
`received` is reachable only once (state machine), stock cannot be double-restored.

### 6. Refund execution branches on payment method

`refund_method` is derived from `orders.payment_method`:

- **card (Stripe):** on `received → refunded`, call the Stripe Refunds API for the
  order's PaymentIntent with `amount = refund_amount_cents`. Set `refund_status =
  pending` and store `stripe_refund_id`. Local `status` becomes `refunded` only after a
  verified `charge.refunded` / `refund.updated` webhook confirms success (idempotent by
  Stripe event id, reusing `payment-integration`'s event store). A failed Stripe refund
  sets `refund_status = failed`, writes a `refund_failed` event, alerts the admin, and
  leaves the return at `received` for retry.
- **bank_transfer / cod:** no API call. The owner records the refund (optional
  `refund_reference`), which sets `refund_status = refunded` and `status = refunded`
  immediately. Physical money movement is the owner's responsibility.

Partial refunds are supported by construction (amount = returned items). Reuse the
existing Stripe client wrapper and env credentials from `payment-integration`; no new
secrets.

### 7. Only paid orders can refund; COD nuance

A refund presupposes the customer paid. `payment_status` must be `paid` (card, or COD
auto-marked paid on delivery, or bank_transfer marked paid) for the refund step to
proceed. For COD/bank orders the "refund" is a manual outbound settlement recorded in
the app. If an order somehow reaches return without `paid`, the owner may still
`approve`/`receive` and restore stock, but the refund step records `refund_status =
none` with a note rather than moving money.

### 8. Ownership and access control mirror orders

Customer return endpoints resolve ownership by `session_id` OR `user_id` (same rule as
`get_order`), returning **404** — never 403 — for non-owners to avoid enumeration.
Admin return endpoints use `require_admin`. A customer may only `cancel` their own
return and only while `requested`.

### 9. Money-moving and state-changing admin actions require a note

`approve`, `reject`, `receive`, and manual `refund` each require a non-empty admin note
persisted to `return_events` (consistent with payment-integration Decision 5/9). Stripe
auto-refund records the system actor + Stripe refund id instead of a note.

### 10. Emails follow the existing durable-outbox pattern

New events queue rows in `order_emails` (reusing the outbox + sweeper) — no new send
path:
- customer `return_approved`, `return_rejected`, `return_refunded`
- admin `admin_return_requested`

The `EmailEvent` literal and `order_{event}.txt` template convention are extended.
Refund email sends only after the refund is confirmed (Stripe webhook) or recorded
(manual), never on the attempt. Templates exist in both `en/` and `bg/`; locale follows
the order's stored `locale` (same as other order emails).

### 11. Revenue is net of confirmed refunds

Dashboard revenue SHALL subtract `refund_amount_cents` for returns whose
`refund_status = refunded`. Pending/failed refunds do NOT reduce revenue. This keeps
the existing "revenue = paid/collected orders" rule and layers a refunds deduction on
top rather than mutating order totals (order snapshots stay immutable).

### 12. Rate limits are conservative MVP constants

- return request creation: max 3 per hour per session, max 10 per day per IP
- customer return cancel: max 5 per hour per session
- admin actions: no additional limit beyond admin auth
- refund webhook: signature-verified, idempotent, no IP limit (same as Stripe webhooks)

These are module constants so production logs can guide tuning.

### 13. Customer-facing return status is coarser than the internal state machine

The internal return state (`requested`/`approved`/`received`/`refunded`/`rejected`/
`cancelled`) plus `refund_status` (`none`/`pending`/`refunded`/`failed`) is operational
detail. Customers see a **coarser** vocabulary, mirroring payment-integration Decisions
10–11 (customer labels vs. admin labels over the same states). Critically, the internal
`refund_status = pending` (a card refund submitted to Stripe, awaiting webhook
confirmation) SHALL NOT surface as a standalone customer state — a bare "pending" that
sits for days reads as broken. It folds into the `received` message.

Customer-facing labels:
- `requested` → `Return requested`
- `approved` → `Approved — send it back`
- `received` (any refund_status other than `refunded`) → `We've received your return — refund on the way`
- `refunded` → `Refunded`
- `rejected` → `Return declined`
- `cancelled` → `Return cancelled`

Admin-facing labels stay operational and expose the refund sub-state:
- `received` + `refund_status = pending` → `Received — Stripe refund pending`
- `received` + `refund_status = failed` → `Received — refund failed (retry)`
- `received` + `refund_status = none` → `Received — awaiting manual refund`

A `refund_status = failed` (Stripe rejected the refund) is never shown to the customer
as failure; to them it remains `received` / "refund on the way" while the owner retries
or settles manually. This keeps the customer experience calm and truthful without
leaking retry churn.

### 14. Terminal Stripe refund failures auto-route to the manual lane (owner confirms)

A card refund can fail two ways: **transient** (network, rate limit, Stripe 5xx) or
**terminal** (Stripe structurally cannot refund the charge — e.g. already refunded,
disputed, or too old). Transient failures stay `refund_status = failed` and are retried
(Decision 6). Terminal failures instead auto-route to the existing manual settlement
lane so the owner can send the money back by hand — the candle is already returned and
stock already restored, so the customer is owed.

Safety rules, because misclassification is asymmetric (wrongly calling a transient error
terminal risks a **double refund** — owner pays by hand *and* Stripe later succeeds):

- **Classify on Stripe's own error code against a tight terminal allowlist; default
  everything else to transient.** An unknown code never triggers the auto-drop-to-manual
  — the dangerous direction requires a known, explicit reason. Terminal allowlist,
  keyed on the Stripe error `code` (or `Refund.failure_reason` when async):
  `charge_already_refunded` (nothing left to refund), `charge_disputed` /
  `charge_disputed` errors (funds held by dispute — refund via dispute flow, not the
  Refunds API), and charge-not-refundable / expired (charge too old or original card
  gone). **Verify exact codes against the current Stripe API-errors and Refund
  `failure_reason` docs at build time; anything not matched stays transient.**
- **Terminal does NOT auto-refund — it auto-*offers*.** The return moves to
  `refund_status = manual_required` with the reason recorded in `return_events`; the
  status stays `received`. Money moves only when the owner explicitly confirms the manual
  refund (→ `refunded`). This preserves the single-human-action guard against
  double-pay.
- **`stripe_refund_id` is the idempotency key.** If a `manual_required` return later
  receives a *succeeded* Stripe refund webhook (race — it went through after we gave up),
  the webhook wins: the return becomes `refunded` via Stripe and the manual path is
  blocked. One refund id, one outcome.
- **Classification lives in both paths.** The synchronous `refund.create` call classifies
  inline; async failures arriving via `refund.updated` webhook classify in the handler.
  Both share the one terminal-code allowlist.

Refund status flow:

```
received ──► (Stripe) ──► pending ──► refunded              [happy path, webhook-confirmed]
                │
                ├─ transient fail ──► failed ──► retry (stays received)
                │
                └─ TERMINAL fail ──► manual_required ──► owner confirms ──► refunded
```

Customer-facing: `manual_required` is folded into the same "refund on the way"
presentation as `pending`/`failed` (Decision 13) — never shown as a problem. Admin-facing:
`received` + `manual_required` → "Received — automatic refund unavailable, settle
manually".

### 15. "One open return per order" is enforced with the checkout concurrency pattern

The "one open return per order" invariant (Decision 3) is a check-then-insert: read
whether an open return exists, and if not, insert a new one. Under concurrency — a
double-clicked "Request return", or a frontend retry of a slow request — two
`POST /v1/orders/{id}/returns` calls can both pass the read before either inserts,
producing two open returns for one order. The blast radius is worse than a duplicate
row: each return can then claim the same `order_item` quantity through the equally
check-then-insert per-item remaining-quantity cap, so more units can be refunded than
were ordered.

This is the same class of race the store already solved for stock oversell and for
duplicate email sends. `create_return` SHALL mirror that pattern with both layers:

- **Serialize the writer.** Wrap the eligibility checks (open-return, per-item
  remaining quantity) and the insert of the `returns` row + `return_items` + `requested`
  event in a single `BEGIN IMMEDIATE` transaction, exactly as `create_order`
  (`order_service.py`) and the cart mutations (`cart_service.py`) do. `BEGIN IMMEDIATE`
  takes SQLite's write lock up front, so the second concurrent request blocks until the
  first commits and then reads the updated state. A deferred `BEGIN` does NOT close the
  gap — its read acquires only a shared lock.
- **Back it with a DB constraint.** Add a partial unique index as the last line of
  defense, directly analogous to `idx_order_emails_sent_unique`
  (`... ON order_emails(order_id, event) WHERE status = 'sent'`):

  ```sql
  CREATE UNIQUE INDEX idx_one_open_return_per_order
      ON returns(order_id)
      WHERE status IN ('requested', 'approved', 'received');
  ```

  Even if application logic regresses, the database physically refuses the second open
  return. The insert violating this index is caught and mapped to the same HTTP 409 the
  "Only one open return per order" requirement already specifies — so the constraint
  failure surfaces as the intended domain error, not a 500.

The per-item remaining-quantity cap has no clean single-column index to back it (it is a
sum across sibling rows), so it relies on Layer A alone: because `BEGIN IMMEDIATE`
serializes writers and the open-return index permits at most one in-flight return per
order, no second return can be concurrently accumulating quantity against the same order.

## Supersedes

This change supersedes `openspec/changes/deferred/stripe-refunds/`. The deferred
proposal's open questions are resolved here:
- **Partial vs. full refunds:** partial supported (by returned items).
- **Refund auto-cancels order / restores stock:** stock restores at `received`; order
  status is NOT auto-changed (`delivered` stays terminal).
- **COD refund status model:** same `returns.status` model, with `refund_method =
  cod_manual` and manual settlement.

## Launch Requirements

- Reuse and re-verify the Stripe webhook path from `payment-integration` for
  `charge.refunded` / `refund.updated`; add local Stripe CLI verification of the refund
  events before marking complete.
- Confirm `delivered_at` exists or is added, and is backfilled for existing delivered
  orders (fall back to `updated_at` for legacy rows, one-time).
- `RETURN_WINDOW_DAYS` documented in `.env.example`.
