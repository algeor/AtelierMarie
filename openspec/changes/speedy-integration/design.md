# Speedy Integration — Design

Reference docs (verify all payloads/fields against these — do not guess):
- REST API: https://api.speedy.bg/web-api.html
- Examples + Postman collection: https://services.speedy.bg/api/api_examples.html
- Error explanations: https://services.speedy.bg/api/api_examples.html#errorsExplanation

Demo creds: user `1996593` / password via `SPEEDY_API_PASSWORD` env. Fictional
client in Speedy's real system → non-billing, but real waybills.

## Decision 1 — Auth, config-driven host & sender identity

Speedy takes `userName` + `password` in the JSON **body** (already done in
`calculate`). Add `speedy_base_url` to `app/config.py` (default
`https://api.speedy.bg/v1`); replace hardcoded `_CALCULATE_URL` and derive all
endpoints (`/calculate`, `/shipment`, `/track`, `/print`) from it. Creds:
`speedy_api_username` / `speedy_api_password` (SecretStr) already exist — wire
demo values via `.env`.

**Sender identity fix (the second, hidden blocker).** `speedy_client.py:77`
sends `"sender": {"clientId": speedy_sender_office_id}` — but that config field
defaults to `""`, has no `.env` value, and is *named* an office id while Speedy's
`clientId` is a numeric registered-client/contract identifier. Consequences:
- Every real Speedy call (door AND office) has been sending `clientId: ""`, so
  door mode has likely been falling back too — not just office mode. The
  "office-ID 400 → €5 fallback" note conflates a recipient-office rejection with
  a (possibly separate) sender rejection.
- The unit tests pass `sender_office_id="sofia-1"` (a slug) against a **mocked**
  httpx client, so a payload Speedy would reject stays green.

Fix: **rename `speedy_sender_office_id` → `speedy_client_id`** (numeric), thread
it into `sender.clientId`. If Speedy's `/shipment` needs a separate drop-off
office, add that as its own verified field — do NOT reuse the pricing client id.
An empty/non-numeric `speedy_client_id` logs a distinct
`speedy_sender_client_id_invalid` warning so a misconfigured sender is
distinguishable from a Speedy outage. This gates BOTH pricing and Decision 3
(shipment create needs the same valid sender identity).

## Decision 2 — Fix office-ID pricing (the Phase A blocker)

Root cause: `pickupOfficeId` must be a numeric int; our office `id` is a slug.
Fix the **data**: repopulate `data/speedy_offices.json` from Speedy's real
office nomenclature so each office carries its true numeric ID. Options:
- Add a `courier_office_id` field (raw numeric) alongside the internal slug
  `id`, thread it through `Office`/`OfficeResponse`/`DeliveryOffice`; OR
- Store the numeric ID directly as `id`.
Decide during implementation by inspecting the real Speedy office feed. Then
`speedy_client.calculate` sends the numeric id as `pickupOfficeId`.

## Decision 3 — Shipment creation (waybill), anchored on the `shipped` transition

New `create_shipment(...)` → `POST {base}/shipment`, building the label from the
order's `delivery` snapshot: real recipient name/phone/address (no placeholder,
unlike calculate). Returns Speedy's parcel/shipment id → persisted as the order's
`tracking_number`.

**Trigger: `confirmed → shipped`, NOT `pending → confirmed`.** The codebase
already models tracking at the ship step, not confirm: `orders` has
`tracking_number`/`tracking_carrier`/`tracking_url` columns, `update_status(...,
"shipped")` *requires* a tracking number today (raises `TrackingRequiredError` →
422), and `tracking_url_for(...)` auto-builds the URL. So an admin already births
a tracking number by hand at ship. Speedy automates producing that same number at
the same transition — we extend the existing single code path rather than adding
a second birthplace at confirm (two birthplaces = two idempotency bugs). This also
keeps confirmation free of an external dependency: a Speedy outage must never
block *confirming* an order, only shipping it. (This supersedes the earlier
"create at confirmation" wording and aligns with Decision 7.)

Flow inside `update_status(order, "shipped")`:
1. validate transition `confirmed → shipped` (exists).
2. if courier is Speedy AND no `tracking_number` supplied → call
   `create_shipment(order snapshot)`; use its returned id as the tracking number.
3. write `status='shipped'` + tracking fields in the **same transaction** (exists).

- **Idempotency:** the existing `if not tracking_number` guard gates the courier
  call — an order that already has a tracking number skips `create_shipment` and
  just sets status. Re-running "ship" never creates a second waybill.
- **Failure:** `create_shipment` raises `ShipmentCreationError` *before* the
  `UPDATE orders`, so the transaction never commits — the order stays `confirmed`,
  never landing in `shipped` without a real waybill. Mapped Speedy error surfaced
  to admin; no silent degrade (unlike pricing).
- **Manual fallback preserved:** automation augments, not replaces. If an admin
  supplies a tracking number by hand (Speedy down, or a non-courier shipment),
  `create_shipment` is skipped — the current manual path still works.
- Store `courier`, `tracking_number`, `label_url`/id on the order.

## Decision 4 — Tracking (read-only, display-only — does NOT drive the state machine)

New `track_shipment(tracking_number)` → `POST {base}/track`. Speedy's status
vocabulary is richer than ours (picked up / in transit / out for delivery /
delivery failed / returned to sender / delivered) and describes *physical
transit*; our 5 order codes (`pending/confirmed/shipped/delivered/cancelled`)
describe the *purchase lifecycle* and are guarded by `VALID_TRANSITIONS`.

**Track normalizes Speedy's code to our own small display enum and surfaces it
read-only — it never calls `update_status`.** Reasons the poll must not advance
the state machine:
- **It would bypass the guard.** `update_status` enforces `VALID_TRANSITIONS`
  and requires tracking on ship. A poller writing `orders.status` becomes a
  second, unguarded writer — the "two birthplaces" problem removed in Decision 3.
- **Speedy has states we can't represent.** "Returned to sender" and "delivery
  failed" have no home in our 5 codes; auto-mapping would drop them or force a
  wrong code. A display label shows them honestly; the state machine can't.
- **`delivered` has a side-effect.** `update_status` auto-marks COD orders
  `paid` on `delivered`. A courier status must never silently mark money
  collected.

Mapping is narrow and one-directional: Speedy code → `courier_status` display
enum in our words (e.g. `in_transit` / `out_for_delivery` / `delivered` /
`returned` / `failed`), shown on order detail (admin + customer). If delivery
should advance the order, that stays a **human confirm**: the admin sees "Speedy
says delivered" and clicks through the guarded `shipped → delivered` transition
(and its COD-paid side-effect) deliberately. Read-only; safe to poll.

## Decision 5 — Label printing

New `print_label(tracking_number)` → `POST {base}/print` returning PDF bytes.
Admin-only endpoint streams the PDF. Depends on Decision 3 (needs a waybill).

## Decision 6 — Error handling

Keep the Phase A pattern for **pricing** (any failure → flat fallback,
`price_source="flat"`, never raises). For **shipment/track/print** do NOT fall
back silently — these are real operations; map documented Speedy error codes
(see errorsExplanation) to typed exceptions and surface to admin. Log the
truncated Speedy error body (as `calculate` already does).

## Decision 7 — Order model & state

`orders` already has `tracking_number`/`tracking_carrier`/`tracking_url`; this
change adds `courier` (+ optional `label id/url`) if not already present. State
machine unchanged (pending→confirmed→shipped→delivered). Waybill is created on
the `confirmed → shipped` transition (Decision 3), so `shipped` implies a
waybill — whether the tracking number came from Speedy automatically or was
entered manually.

## Verification plan (with demo account)

1. Live `calculate`: door quote (Садово+postcode) and office quote (real
   numeric id) both return `price_source="live"`, non-fallback — **with a known-good
   numeric `speedy_client_id` in `sender.clientId`**. Confirm what value Speedy
   accepts there (login user `1996593`? a separate client object id?); this single
   answer unblocks both pricing and Decision 3.
2. `create_shipment` for a test order → real Speedy tracking number returned +
   stored; confirm no double-creation on retry.
3. `track_shipment` on that number → status returned + mapped.
4. `print_label` → valid PDF bytes.
5. Error paths: bad office id, missing weight, bad creds → mapped to typed
   errors, logged with body, no crash.
6. Full backend suite + ruff green.

## Open questions
- Exact value Speedy accepts for `sender.clientId` on the demo account (the
  login user `1996593`, or a distinct numeric client-object id?). Verify FIRST —
  gates pricing and shipment create.
- Exact Speedy office nomenclature endpoint + field for numeric ID (confirm
  against docs / live feed).
- Does the demo account permit `/shipment` create, or calculate-only? Verify
  before building Decision 3.
- Label format/size options (`/print` params).
