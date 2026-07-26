## 1. Config & constants

- [ ] 1.1 Add `data_retention_years: int` to `app/config.py` (pydantic Settings, `ge=1`, conservative default matching statutory accounting-record period) with a comment noting the value is a legal determination
- [ ] 1.2 Add the `[erased]` placeholder to a single source of truth (reuse `_ERASED_PLACEHOLDER` in `gdpr_service.py`; promote to `app/constants.py` if referenced elsewhere)

## 2. Erasure service (`app/services/gdpr_service.py`)

- [ ] 2.1 Add a subject-resolution helper that, given any subset of `email` / `user_id` / `session_id`, returns the matched `order_id`s (`customer_email` OR `user_id` OR `session_id`), comment row keys (`user_id` OR `session_id`), and `contact_messages` ids (by `email`)
- [ ] 2.2 Extend `anonymize_order_emails` OR add an order-row scrub that NULL-ifies/placeholders `customer_email`, `customer_name`, `delivery_details`, `notes` on **all** matched orders regardless of age (guarded `WHERE ... != '[erased]'` for idempotency; leave `total_cents`, `status`, `order_items` untouched)
- [ ] 2.3 Add hard-delete of resolved `comments` rows (by `user_id`/`session_id`)
- [ ] 2.4 Add `users` PII erasure using **per-subject unique** placeholders (email/google_id are `UNIQUE NOT NULL`, cannot be NULLed or set to a shared constant): `email = 'erased-'||id||'@invalid'`, `google_id = 'erased-'||id`; set `name`/`avatar_url` NULL; delete the subject's active `sessions` rows. Re-run must match the row by `id`, not email.
- [ ] 2.5 Add `contact_messages` scrub (by `email`): NULL-ify `name`, `email`, `message`, `ip_address`
- [ ] 2.6 Do NOT delete `suppressed_emails` on erasure — leave the do-not-contact record in place (Recital 65 / Art. 21); bounded age-out stays in the sweep only
- [ ] 2.7 Compose the above into `erase_data_subject(*, email=None, user_id=None, session_id=None)` running in a single `BEGIN`/`COMMIT` transaction, returning per-table affected counts
- [ ] 2.8 Ensure the whole operation is idempotent (second run changes zero rows) and structured-logs a summary (use redaction helper for any email in logs)

## 3. Retention sweep

- [ ] 3.1 Add `sweep_orders_past_retention()` to `gdpr_service.py`: hard-delete orders with `created_at` older than `data_retention_years`, deleting **all three** FK children (`order_emails`, `order_email_send_claims`, `order_items`) first and the order row last, in a transaction (foreign_keys is ON)
- [ ] 3.2 Confirm `age_out_suppressed_emails` is included in the sweep path; keep existing `cleanup_old_contact_messages` behavior
- [ ] 3.3 Wire the sweep into `cleanup_runtime_records()` in `app/main.py` so it runs on the existing hourly loop; catch/log its own errors so a failure never propagates

## 4. Admin API

- [ ] 4.1 Add request/response Pydantic models to `app/models/admin.py` (`ErasureRequest` with optional email/user_id/session_id; `ErasureResult` with per-table counts)
- [ ] 4.2 Add `POST /v1/admin/gdpr/erasure` route in `app/routes/admin.py` guarded by `require_admin`; validate that at least one of email/`user_id` is present (422 otherwise); call `erase_data_subject`; return counts
- [ ] 4.3 Confirm no Layer 2 imports and route stays thin (delegates to service)

## 5. Tests

- [ ] 5.1 Service test: order PII NULL-ified on all matched orders regardless of age, `total_cents`/`order_items` preserved
- [ ] 5.2 Service test: `order_emails.recipient` scrubbed, `status`/unique-sent index intact
- [ ] 5.3 Service test: comments hard-deleted; users PII uses per-subject unique placeholder (email/google_id), sessions removed
- [ ] 5.4 Service test: two different users erased in sequence do NOT collide on the `users` UNIQUE indexes
- [ ] 5.5 Service test: `contact_messages` matched by email are scrubbed; `suppressed_emails` entry is NOT deleted by erasure
- [ ] 5.6 Service test: idempotent re-run changes zero rows (users re-matched by id after email scrub)
- [ ] 5.7 Service test: subject resolution unions anonymous (`session_id`) + logged-in (`user_id`) orders
- [ ] 5.8 Sweep test: order past window hard-deleted incl. `order_email_send_claims` child (no FK error); order within window untouched; sweep error is caught and does not raise
- [ ] 5.9 Route tests: admin erases by email (counts returned); 422 on session-only request; 401/403 unauthenticated; not-found returns success with zero counts
- [ ] 5.10 Run `make test-backend` and `make lint`; ensure ≥80% coverage on new code

## 6. Docs

- [ ] 6.1 Note the chosen `data_retention_years` value and lawful-basis rationale (Art. 6(1)(c) / 5(1)(e)) in the change's design.md Open Questions resolution, and flag for DPO confirmation
