## Why

The right to erasure (GDPR Art. 17) is effectively unimplemented. `app/services/gdpr_service.py`
holds two helpers (`anonymize_order_emails`, `age_out_suppressed_emails`) that have **zero callers** —
no route, no admin action, no scheduled job invokes them. The most sensitive PII we hold — the
`orders` row (`customer_email`, `customer_name`, `delivery_details` physical address JSON, `notes`)
and `comments` (`display_name`, `body`) — has **no erasure path at all**. A data-subject erasure
request today cannot be fulfilled, which is exactly the real-world failure regulators flagged in the
2025 Coordinated Enforcement action on the right to erasure.

## What Changes

- Add a **consolidated erasure operation** that, for a data subject identified by any of
  email / `user_id` / `session_id`, resolves all their records and removes PII across `orders`,
  `order_emails`, `comments`, and (for a logged-in subject) `users`.
- **Resolve the Art. 17 vs. Art. 6(1)(c) tension via NULL-ification, not deletion**: during the
  legal tax/accounting retention window, order PII is overwritten with placeholders while order
  structure and financial totals (`total_cents`, `order_items` snapshots) are retained; only after
  the window elapses are order rows hard-deleted.
- Add an **admin-triggered erasure action** (POST endpoint) so the shop owner can action a request.
- Add a **scheduled retention sweep** that hard-deletes orders past the retention window and
  ages out other time-bounded PII, wired into the existing cleanup loop in `app/main.py`.
- Add a `data_retention_years` (orders) config setting; keep the existing
  `contact_message_retention_days` and `suppressed_emails` age-out.

Non-goals: subject **access/portability** export (Art. 15/20) and a public self-service erasure UI —
tracked separately. This change delivers the executable erasure + retention backbone.

## Capabilities

### New Capabilities
- `gdpr-erasure`: Service-layer operation that erases/anonymizes a data subject's PII across all
  Layer 1 tables, honoring order-snapshot immutability and the retention window.
- `gdpr-retention-sweep`: Scheduled background job that enforces storage-limitation — hard-deletes
  orders past the retention window and ages out time-bounded PII.
- `gdpr-admin-api`: Admin-only endpoint to trigger erasure for a given data subject and report what
  was affected.

### Modified Capabilities
<!-- No existing spec's REQUIREMENTS change; this is additive. Wiring touches admin routes and the
     main.py cleanup loop at the implementation level only. -->

## Impact

- **Code:** `app/services/gdpr_service.py` (expand), `app/routes/admin.py` (new endpoint),
  `app/models/admin.py` (request/response models), `app/main.py` (retention sweep in cleanup loop),
  `app/config.py` (retention setting). SQLite only — no Layer 2 imports.
- **Data:** No schema change required (PII is NULL-ified/placeholdered in place); hard-delete
  respects `order_items` FK and the `idx_order_emails_sent_unique` partial index.
- **Compliance:** Makes Art. 17 executable; documents lawful basis for retention (Art. 6(1)(c)) and
  storage limitation (Art. 5(1)(e)).
- **Tests:** New service + route tests; must verify erasure leaves order structure/financials intact
  and that the sweep only deletes past-window rows.
