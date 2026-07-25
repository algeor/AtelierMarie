# Payment Integration — Exploration Notes

Recorded from the /opsx:explore session on 2026-07-25.

## Open Questions Resolved

| # | Question | Decision |
|---|----------|----------|
| 1 | Does Stripe payment auto-advance order to `confirmed`? | No — webhook updates `payment_status` only. Admin still manually confirms. |
| 2 | Is COD `payment_status` marked by system or admin? | System — auto-`paid` when `order_status → 'delivered'`. COD contract: delivery = cash collected. |
| 3 | Checkout Sessions vs. embedded Elements? | Checkout Sessions. PostgreSQL migration is zero-impact (Stripe refs are plain TEXT). |
| 4 | Stock decrement timing? | At order creation (current behavior preserved). Decrement-at-webhook creates oversell race with COD architecture. |
| 5 | Shipping cents passed to Stripe? | Server-authoritative. Client sends delivery choice; server calculates; Stripe charges `order.total_cents`. ±50 cent tolerance check eliminated. |
| 6 | "placed" email for card orders? | Delay to `payment_intent.succeeded` webhook. Add `payment_pending` event for immediate acknowledgment. |
| 7 | Bank transfer IBAN in email or UI? | Both. IBAN/BIC from settings config. `payment_reference = order_id_short`. |
| 8 | Failed Stripe payment — cancel or pending? | Leave pending (`payment_status='failed'`) + 24h auto-cancel job for card+pending orders. "Retry payment" link on order detail. |
| 9 | Stripe dedup approach? | Dedicated `stripe_events` table. Same pattern as `order_emails`. `INSERT OR IGNORE` on `event_id`. |

## Pre-Existing Bug Surfaced

`order_cancelled` email templates (en + bg) say "refund processed / will be
returned to your original payment method" for ALL cancellations. This is wrong
for COD orders — no money changed hands. Must be fixed before any payment
integration ships. Fix: guard refund language on `payment_method == 'card' and
payment_status == 'paid'`.

## Golden Standard Divergences (Justified)

| Decision | GS | Ours | Verdict |
|----------|----|------|---------|
| Stock decrement timing | At webhook | At order creation | Justified: COD constraint forces order-first architecture |
| COD auto-advance on delivery | Explicit event only | Auto on `delivered` | Acceptable: no real-time courier payment signal in BG |
| "placed" email for card | Immediate | Delayed to webhook | UX risk accepted; `payment_pending` mitigates it |

## Recommended Phasing

Phase 1 (no Stripe): COD + bank transfer. DB columns, admin mark-paid, IBAN
in email/UI, fix cancelled template. Zero external dependencies.

Phase 2: Stripe card. `payment_service.py`, webhook handler, `stripe_events`
table, `payment_pending` templates, 24h auto-cancel job.
