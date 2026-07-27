# Stripe Refunds - Deferred Proposal

> **SUPERSEDED (2026-07-27) by `openspec/changes/product-returns/`.** Automated Stripe
> refunds are delivered there as the refund-execution half of the product-return flow
> (card auto-refund, partial refunds by returned items, refund webhook confirmation).
> The open questions below are resolved in that change's `design.md` ("Supersedes"
> section). This deferred proposal is kept for history only — do not implement it
> standalone.

## Motivation

Stripe refunds should eventually be manageable from the admin panel so payment
state, order state, and audit history stay aligned without requiring manual
cross-checking in the Stripe Dashboard.

## Deferred Scope

- Add admin refund action for eligible paid Stripe orders.
- Call Stripe Refunds API from the backend using env-held Stripe credentials.
- Support full refunds first; partial refunds require separate product/accounting
  decisions.
- Record refund requests and Stripe refund events in `payment_events`.
- Update local payment state only after Stripe confirms the refund or a verified
  refund webhook is processed.

## MVP Boundary

The payment MVP should not automate refunds. Admin handles refunds in the Stripe
Dashboard, while the app records refund-related Stripe events as audit-only and
does not mutate order/payment state from refund webhooks yet.

## Open Questions

- Are partial refunds needed, or are full-order refunds enough?
- Should refunding automatically cancel unfulfilled orders and restore stock?
- Should refunded pay-on-delivery orders use the same local status model, even
  though no Stripe refund exists?
