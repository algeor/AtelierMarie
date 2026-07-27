# Returns & Refunds — Exploration

> **Status:** Thinking artifact. No change proposed yet. This captures *what we
> should offer* for returns and *how the system could support it*, so a real
> change can be scoped later. Nothing here is a commitment.

## Context

AtelierMarie sells luxury candles online. Today the store has **no returns
concept at all** — the order lifecycle ends at `delivered` (a terminal state) and
the only "money back" path is **cancellation before shipping**, which restores
stock in the same transaction.

Two facts about the current system drive almost every decision below:

1. **There is no payment integration.** `POST /v1/orders` records no
   `payment_method`, captures no card, and holds no payment token. Combined with
   the Speedy/Econt courier stack, the working assumption is **cash-on-delivery
   (наложен платеж)** — the customer pays the courier on receipt.
   → **A refund cannot be a card reversal. It is a bank transfer** (or store
   credit). This shapes the whole refund UX.

2. **`delivered` is terminal.** The state machine is
   `pending → confirmed → shipped → delivered`, with cancel allowed only from
   `pending`/`confirmed`. Returns happen *after* delivery — so returns cannot be
   just "one more transition" without rethinking the terminal invariant.

```
        CURRENT ORDER LIFECYCLE
        ───────────────────────

  pending ──▶ confirmed ──▶ shipped ──▶ delivered   ⟵ TERMINAL, no path onward
     │            │
     └── cancel ──┘  (restores stock)

        RETURNS LIVE HERE ─────────────────▲
        (nothing models this today)
```

## Why candles make this non-generic

Returns policy is usually a solved, boring thing. Candles complicate it:

- **Used = destroyed.** A lit candle can't be resold. Restock logic must be
  condition-aware, not automatic like cancellation.
- **Fragile.** Glass vessels break in transit → "damaged on arrival" will be a
  common, legitimate reason. Photo evidence matters.
- **Hygiene/seal angle.** EU withdrawal right has an exception for goods
  "sealed for health/hygiene reasons, unsealed after delivery." Whether we lean
  on that for candles is a **policy choice**, not a given.
- **Scent is subjective.** "Didn't like the smell" is the #1 change-of-mind
  reason for candles and is *not* a defect. We need a stance on it.

## The legal floor (EU / Bulgaria)

This isn't optional — it's the minimum we must offer, and the policy sits *on top*.

- **14-day withdrawal right** for distance sales (Закон за защита на
  потребителите / EU Consumer Rights Directive 2011/83). Customer can return for
  **any reason or none**, from the day they receive the goods.
- Refund due **within 14 days** of us getting the goods back (or proof of return).
- **Defective goods** are separate and stronger: 2-year conformity guarantee;
  seller pays return shipping and refunds fully.
- Possible **exemptions** we *may* invoke: sealed-for-hygiene goods unsealed after
  delivery; personalised/custom items. ← decide explicitly, don't drift into them.

> Takeaway: "change of mind within 14 days" must be honoured regardless of what
> marketing wants. The knobs are *shipping cost, refund method, and condition
> proof* — not whether to accept at all.

## Two return tracks (they behave differently)

```
                    ┌─────────────────────────────────────┐
                    │            RETURN REASON             │
                    └─────────────────────────────────────┘
                       │                            │
        ┌──────────────▼─────────────┐  ┌───────────▼──────────────────┐
        │  DEFECTIVE / DAMAGED / WRONG │  │  CHANGE OF MIND (withdrawal) │
        │  ("our fault")               │  │  ("just because")            │
        ├──────────────────────────────┤  ├───────────────────────────────┤
        │ • seller pays return shipping│  │ • customer usually pays       │
        │ • full refund incl. orig ship│  │   return shipping             │
        │ • photo evidence             │  │ • must be unused/unlit/sealed │
        │ • replacement often offered  │  │ • 14-day window               │
        │ • no "unused" requirement    │  │ • refund excl. orig shipping? │
        └──────────────────────────────┘  └───────────────────────────────┘
```

Any policy and any data model has to distinguish these two, because who-pays and
what-condition-is-required diverge.

---

## Policy options (what we OFFER)

Each row is a decision. Recommended default in **bold**, but all are live.

| Dimension            | Options                                                                                     | Lean |
|----------------------|---------------------------------------------------------------------------------------------|------|
| **Window**           | 14 days (legal min) · **30 days (goodwill, easy to market)** · 14 defect-only + 30 unused   | 30-day for change-of-mind reads as premium; keep defect claims at the 2-yr legal guarantee |
| **Condition (change-of-mind)** | **Unused, unlit, original packaging, seal intact** · any condition (generous) | Protects resale; aligns with hygiene-seal stance |
| **Who pays return shipping** | Customer for change-of-mind, **we pay for defect/damage/wrong** · we always pay (premium) · customer always pays | Split is standard & fair; "we always pay" is a brand flex if margins allow |
| **Refund method**    | **Bank transfer (COD reality)** · store credit · customer's choice of either                | No card to reverse; store credit optionally sweetened (e.g. +10%) |
| **Refund scope**     | Item price only · **item price + original shipping if defect, item only if change-of-mind** · always full | Matches EU: full for defect; original outbound shipping needn't be refunded on partial change-of-mind |
| **Restocking fee**   | **None** · small % for opened-but-unused                                                    | Fees feel cheap for a luxury brand |
| **Non-returnable**   | **Used/lit candles; personalised items; (optional) final-sale/clearance**                   | Must be stated up front to be enforceable |
| **Replacement path** | Offer replacement *or* refund for defects · refund only                                     | Replacement keeps the sale & the customer |
| **Proof**            | **Photos required for damage/defect** · none · photos always                                | Cuts fraud on the "our fault" track without friction on change-of-mind |

Open policy questions:

- Do we invoke the **hygiene-seal exemption** to refuse *unsealed* change-of-mind
  returns? (Legally defensible; needs the product to actually ship sealed.)
- Are **sale/clearance items** final, or same policy? (Marketing input.)
- Store credit as **default or opt-in**? Bonus credit to nudge it?
- Return **drop-off** — courier office return (Econt/Speedy) vs customer ships
  however. Do we generate a return label / cover the COD-return cost?

---

## System options (how we BUILD it)

Three shapes, cheapest first. This is the main architectural fork.

### A) Extend the order state machine
```
delivered ──▶ return_requested ──▶ returned ──▶ refunded
                     │
                     └──▶ return_rejected
```
- ➕ One table, familiar pattern, small diff.
- ➖ Breaks the "delivered is terminal" invariant everywhere it's assumed.
- ➖ Models **one return per order** — no partial returns (return 1 of 3 candles),
  no second return. Candles-in-a-set will hit this fast.
- ➖ Refund amount, reason, condition, photos all bolt awkwardly onto `orders`.

### B) Separate `returns` entity (recommended for the real build)
```
  orders (unchanged, stays "delivered")
     │ 1
     │
     │ N
  returns ─────────────┐
   id, order_id,       │ 1
   reason_track,       │
   status, refund_cents│ N
   refund_method,      ▼
   created_at      return_items
                    return_id, order_item_id, qty, condition, restock?
```
- ➕ Clean: one order → many returns; each return → specific line items & qty.
- ➕ Partial returns, per-item condition, per-item restock decision.
- ➕ Own lifecycle (`requested → approved → received → refunded / rejected`)
  without touching the order state machine or its terminal invariant.
- ➕ Refund is first-class data (amount, method, reference, who/when).
- ➖ More schema, new service (`return_service.py`), new admin views, new specs.

```
        RETURN LIFECYCLE (option B)
        ───────────────────────────
  requested ─▶ approved ─▶ received ─▶ refunded
      │            │
      └── rejected ┘
   (photos, reason,   (admin inspects,   (bank transfer
    track captured)    sets condition,    ref recorded,
                       restock per item)  stock++ if resellable)
```

### C) Policy doc only, manual admin handling (MVP / today)
- Publish the returns **policy page** + a **FAQ / contact-driven flow**: customer
  emails/contacts, admin handles refund by hand (bank transfer), manually adjusts
  stock and adds an order note.
- ➕ Zero data-model work. Legally compliant *now* (policy is what the law cares
  about; the tooling is our convenience).
- ➕ Ships immediately; validates real return volume before we build tooling.
- ➖ No audit trail, no metrics, doesn't scale, refund tracking lives in email.

```
   MATURITY LADDER
   C (policy + manual)  ──▶  B (returns entity + admin UI)  ──▶  self-serve portal
   ship now, learn volume     build when volume justifies       far future
```

### Cross-cutting build concerns (any option beyond C)

- **Restock ≠ cancellation.** Never auto-increment stock on return. Restock only
  the line items an admin marks *resellable* (unopened). Reuse the transactional
  stock-update code path, gated on condition.
- **Refund record.** Even with no payment gateway, store `refund_method`,
  `refund_cents`, and a free-text `refund_reference` (bank txn id) for the audit
  trail. Wire to Stripe refunds *only if/when* card payment lands.
- **Emails.** New transactional templates (return received, refund issued) via the
  existing durable-outbox email service, en + bg locales.
- **GDPR interaction.** Returns reference `customer_email` / bank details →
  in-scope for the `gdpr-data-erasure` scrub. Coordinate field list.
- **Layer boundary.** All returns logic is Layer-1 (money + stock). No analytics
  coupling.

---

## A first cut, if we had to pick today

- **Policy:** 30-day change-of-mind (unused/unlit/sealed, customer pays return
  shipping) + defect/damage track (we pay, full refund incl. original shipping,
  photos). Refund via **bank transfer**; store credit offered as a faster option.
  Used candles & personalised items non-returnable, stated on the policy page.
- **Build:** Start at **C** — publish the policy page + FAQ, handle manually — and
  scope **B** (the `returns` entity) as the follow-up once we see real volume.
  Skip **A**; the one-return-per-order ceiling isn't worth the invariant it breaks.

## Open questions / next step

1. Confirm the payment reality: is it **100% cash-on-delivery**, or is card
   payment on the roadmap? (Decides whether refunds ever become card reversals.)
2. Marketing/owner call on the policy knobs above (window, who-pays, store-credit
   bonus, sale-item finality, hygiene-seal stance).
3. If we proceed past C: create a change proposal for the `returns` entity
   (option B) — new capability `returns-management`, modified `admin-orders`,
   new email templates, GDPR field coordination.
4. Sanity-check the hygiene-seal exemption with how candles are actually packaged
   (are they shipped sealed?) before relying on it to refuse returns.
