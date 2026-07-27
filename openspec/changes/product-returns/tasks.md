# Product Returns - Tasks

## 1. Schema And Migration

- [ ] 1.1 Add `returns` table (id, order_id, session_id, user_id, status, reason_code, reason_text, refund_amount_cents, refund_method, refund_status, stripe_refund_id, refund_reference, created_at, updated_at, received_at, refunded_at).
- [ ] 1.2 Add `return_items` table (id, return_id, order_item_id, product_id, quantity, price_cents) with FK to `order_items`.
- [ ] 1.3 Add append-only `return_events` table (id, return_id, event_type, actor, admin_note, metadata JSON, created_at).
- [ ] 1.4 Add `orders.delivered_at` column; stamp it on the `shipped → delivered` transition; one-time backfill for legacy delivered orders (fallback `updated_at`).
- [ ] 1.5 Add indexes: `returns(order_id)`, `returns(status)`, `returns(session_id)`, `returns(user_id)`, `returns(stripe_refund_id)`, `return_events(return_id)`.
- [ ] 1.6 Add partial unique index `idx_one_open_return_per_order ON returns(order_id) WHERE status IN ('requested','approved','received')` — the DB-level backstop for "one open return per order" (mirrors `idx_order_emails_sent_unique`).

## 2. Configuration And Constants

- [ ] 2.1 Add `RETURN_WINDOW_DAYS` (default 14) to `app/config.py` and `.env.example`.
- [ ] 2.2 Add `ReturnStatus`, `ReturnReasonCode`, `RefundMethod`, `RefundStatus` (incl. `manual_required`) literals, the return state-transition map, and the terminal Stripe-refund error-code allowlist to `app/constants.py`.
- [ ] 2.3 Add return rate-limit constants (request creation per session/IP, cancel per session).

## 3. Models

- [ ] 3.1 Add `app/models/returns.py`: `CreateReturnRequest` (items + reason), `ReturnItem`, `ReturnResponse`, `ReturnListResponse`, `ReturnEvent`, admin action request bodies (note-required).
- [ ] 3.2 Extend order detail response models with per-item `returned_quantity` / `returnable_quantity` and an order-level `is_returnable` flag.
- [ ] 3.3 Frontend `lib/types.ts` mirrors of the new return models.

## 4. Return Service

- [ ] 4.1 Implement `app/services/return_service.py` with return exceptions (not-found, not-delivered, window-closed, return-open, quantity-exceeded, invalid-transition, note-required).
- [ ] 4.2 `create_return`: under `BEGIN IMMEDIATE` (serialize concurrent requests, per Decision 15 — mirrors `create_order`), validate delivered + window + one-open-return + per-item remaining quantity; compute `refund_amount_cents` from `order_items` snapshots; derive `refund_method` from `payment_method`; insert return + items + `requested` event; queue `admin_return_requested` email — all in one transaction. Map the `idx_one_open_return_per_order` constraint violation to HTTP 409.
- [ ] 4.3 Return state machine: `approve`, `reject`, `receive`, `refund`, customer `cancel`, each validating the transition and (for admin state/money actions) requiring a note.
- [ ] 4.4 `receive`: restore stock per item via the product-service restore path and stamp `received_at`, in one transaction.
- [ ] 4.5 Ownership-checked reads (`get_return`, `list_returns_for_order`) returning 404 for non-owners; admin reads without ownership check.

## 5. Refund Execution

- [ ] 5.1 Card path: re-verify amount, call Stripe Refunds API for the order's PaymentIntent, set `refund_status = pending`, store `stripe_refund_id`, write `refund_attempted` event.
- [ ] 5.2 Transient Stripe failure: `refund_status = failed`, `refund_failed` event, admin alert, return stays `received` (retryable).
- [ ] 5.3 Bank/COD manual path: record optional `refund_reference`, set `refund_status = refunded` + status `refunded`, stamp `refunded_at`, write `refund_confirmed` event, queue `return_refunded` email.
- [ ] 5.4 Guard: refund only proceeds when the order `payment_status = paid`; otherwise record `refund_status = none` with a note.
- [ ] 5.5 Terminal Stripe failure classification: shared terminal-code allowlist (default all other codes to transient), applied in both the `refund.create` call and the `refund.updated` webhook; on terminal → `refund_status = manual_required`, stay `received`, record reason, no money moved.
- [ ] 5.6 Allow the manual refund action for card orders in `manual_required`; block it once a succeeded Stripe webhook lands for the same `stripe_refund_id` (Stripe wins).

## 6. Webhooks

- [ ] 6.1 Extend `webhook_service.py` allowlist with `charge.refunded` / `refund.updated`; verify signature and process idempotently by Stripe event id (reuse the payment-integration event store).
- [ ] 6.2 On confirming webhook: match `stripe_refund_id`, set `refund_status = refunded`, status `refunded`, stamp `refunded_at`, write `refund_confirmed` event, queue `return_refunded` email.
- [ ] 6.3 Ignore duplicate refund events idempotently.

## 7. Routes

- [ ] 7.1 Customer: `POST /v1/orders/{id}/returns`, `GET /v1/orders/{id}/returns`, `POST /v1/orders/{id}/returns/{return_id}/cancel` (rate-limited).
- [ ] 7.2 Admin: `GET /v1/admin/returns` (status filter, pagination), `GET /v1/admin/returns/{return_id}` (detail + timeline), approve/reject/receive/refund actions.
- [ ] 7.3 Map return-service exceptions to the standard error envelope (422/404/409/429).
- [ ] 7.4 Include returned/returnable quantities and `is_returnable` in order detail responses.

## 8. Emails

- [ ] 8.1 Extend `EmailEvent` with `return_approved`, `return_rejected`, `return_refunded`, `admin_return_requested`.
- [ ] 8.2 Add `en/` and `bg/` templates: `order_return_approved.txt`, `order_return_rejected.txt`, `order_return_refunded.txt`, `admin_return_requested.txt`.
- [ ] 8.3 Queue events at the correct transitions; refund email only after confirmed/recorded.

## 9. Admin Dashboard / Revenue

- [ ] 9.1 Subtract `refund_amount_cents` of `refund_status = refunded` returns from dashboard revenue (net revenue); leave pending/failed out.

## 10. Frontend

- [ ] 10.1 Customer: "Request return" flow on delivered orders (item + quantity picker, reason), guarded by `is_returnable`.
- [ ] 10.2 Customer: return status + refund progress in order history/detail; cancel-while-requested action.
- [ ] 10.3 Admin: returns queue page + sidebar nav, return detail with item breakdown + timeline, approve/reject/receive/refund modals (note required).
- [ ] 10.4 Admin: linked returns + "start return" affordance on order detail; net-of-refunds revenue display.
- [ ] 10.5 `lib/mock-api.ts` mocks for all return endpoints; i18n labels in `en.json` + `bg.json`.
- [ ] 10.6 Customer/admin return status label mapping (Decision 13): coarse customer labels; `pending`/`failed`/`manual_required` all fold into the `received` "refund on the way" presentation; admin labels expose the refund sub-state.

## 11. Tests And Verification

- [ ] 11.1 Service tests: eligibility (delivered/window/one-open/quantity cap), amount computation from snapshots, state machine (valid + invalid), receive-restores-stock-once.
- [ ] 11.2 Refund tests: card auto-refund pending → webhook confirm, Stripe failure retry, manual bank/COD recording, refund guard on unpaid orders.
- [ ] 11.3 Route tests: ownership 404, admin auth, note-required 422, rate-limit 429, second-open-return 409, concurrent duplicate requests yield exactly one open return (the other 409s).
- [ ] 11.4 Webhook tests: signature rejection, idempotent duplicate refund event, refund confirmation side effects.
- [ ] 11.5 Revenue test: confirmed refund reduces revenue; pending refund does not.
- [ ] 11.6 Frontend tests: request flow, returnable gating, admin action modals, customer status display.
- [ ] 11.7 Local Stripe CLI verification of refund webhook events; update `.env.example` and docs.
