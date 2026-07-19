# Email Notifications — Design Gap Analysis

> ℹ️ **Superseded provider (2026-07-19):** this audit predates the switch from
> **Resend → Zoho ZeptoMail (EU)** and from a `send.` subdomain → **root domain**.
> References below to Resend, Svix/`whsec_`, the 100/day cap, and the idempotency
> key are historical. Current design: `proposal.md`, `design.md` (Decisions 1, 14,
> 15, 24), the specs, and `EMAIL_SETUP.md`.
>
> ℹ️ **Superseded dispatch model (2026-07-19):** this audit also predates the switch
> from **fire-and-forget `BackgroundTasks` → durable transactional outbox + asyncio
> sweeper** (design Decision 25). References below to `BackgroundTasks` as the
> delivery mechanism are historical; item **#18 (in-flight loss)** is now **resolved**
> — see the footnote on that item.

_Generated from a research + multi-agent review pass (2026-07-15). Four reviewers examined the proposal/design/specs against the real codebase along four lenses: correctness & integration, security & privacy, testing & observability, architecture & scope. Gaps found independently by multiple reviewers are marked ⚑ (high confidence)._

> Several blockers below are corrections to specs authored during this same session — see "Corrections to already-written artifacts" at the end for the exact edits needed.

---

## 🔴 Blockers — resolve before implementation

### 1. ⚑ "Event" vocabulary has no canonical form (spelled 4 ways)
The `event` token is the spine of the feature — it appears in the `order_emails.event` column, template filenames, the idempotency key, the renderer path, and route logic — yet no enum is defined and it is already inconsistent:

| Concept | OrderStatus | log enum (design.md:154) | template file | idempotency key (design.md:231) |
|---------|-------------|--------------------------|---------------|----------------------------------|
| order placed | `pending` | `placed` | `order_placed.txt` | `order-placed/<id>` |

`tasks.md` 8.2 fires `send_order_email(event="pending")` → renderer looks for `order_pending.txt` → miss → locale fallback → miss → **email silently skipped**, and idempotency/key strings won't match.

**Fix:** define one `EmailEvent = Literal["placed","shipped","delivered","cancelled","admin_new_order"]` in `app/constants.py` (CLAUDE.md mandates `constants.py` for cross-module strings) plus an explicit `OrderStatus → EmailEvent` map (`pending→placed`, `confirmed→None`). Pin which spelling flows into filenames vs keys.
_Evidence: order_service.py:206; tasks.md:71; design.md:154,164,231; models/orders.py:7_

### 2. ⚑ `order_emails` idempotency is a TOCTOU race — no `UNIQUE(order_id, event)`
The DDL in design.md Decision 11 has no unique constraint. Idempotency is "check for a sent row, then insert" — two concurrent status updates (admin double-click, client retry, or multiple uvicorn workers under systemd) both read "none," both send, both insert → duplicate customer email. Resend's `Idempotency-Key` (Decision 14) only guards duplicate POSTs within its 24h window; it does not prevent two of our rows or two distinct API calls that each pass the local check.

**Fix:** add a DB-backed send claim keyed by `(order_id, event)` plus a partial unique index on successful sends; acquire the claim before sending, insert the `sent` row only after provider success, and add a concurrency test firing two sends for the same (order_id, event) asserting one provider call while the claim is active.
_Evidence: design.md:150-161; email-service/spec.md idempotency scenario_

### 3. ⚑ Idempotency scenario tests an impossible state transition
The justifying scenario `shipped → confirmed → shipped` cannot happen: the transition map is strictly forward with no back-edges (`shipped:{delivered}`, `delivered:set()`, `cancelled:set()`), and same-state re-entry is rejected with 422. No customer-facing event can fire twice through the API. The table's **audit + future re-send** value is real; the **dedup rationale and this scenario are not** — an implementer would write a test for an unreachable path.

**Fix:** rewrite Decision 11's rationale (drop the toggle justification; keep audit + re-send + defense-in-depth against duplicate API calls) and remove/replace the "status toggled back and forth" spec scenario.
_Evidence: order_service.py:23-29,463; admin.py:420_

### 4. ⚑ Migration approach is invalid SQLite and misses the existing helper
`ALTER TABLE orders ADD COLUMN … IF NOT EXISTS` is a **syntax error** in SQLite. The codebase already has the correct idempotent pattern — `_add_column_if_missing()` (`database.py:310-319`, driven by `PRAGMA table_info`), used for the `preferred_locale` migration (`database.py:329-337`). Also: adding columns only to the `CREATE TABLE IF NOT EXISTS` block means **existing databases never receive them** and crash on the checkout INSERT / reads.

**Fix:** add `tracking_*` and `locale` columns via `_add_column_if_missing` inside `_migrate_existing_schema` **and** to `_SCHEMA_SQL` for fresh DBs. `order_emails` is fine via `CREATE TABLE IF NOT EXISTS`. Correct the wording in proposal.md:117-121 and design.md:186-191.
_Evidence: database.py:61-74,283,310-337_

### 5. ⚑ "Signature-verified" webhook is dangerously underspecified
Resend signs webhooks with **Svix** (`svix-id`, `svix-timestamp`, `svix-signature`; HMAC-SHA256 over `{id}.{timestamp}.{raw_body}`; secret prefixed `whsec_`). Missing from the design:
- **No config field** for the signing secret (`config.py` has `email_api_key` but no `resend_webhook_secret`; `.env.example` has none) — cannot be built as specified.
- **No replay protection** — must reject stale `svix-timestamp` (±5 min). Without it, a captured valid webhook can be replayed to suppress an arbitrary customer address (denial-of-email).
- **No raw-body requirement** — signature is over raw bytes; FastAPI auto-parse / body-reading middleware breaks it. Must `await request.body()` before parsing.
- **No constant-time compare** — use `hmac.compare_digest` (as `auth.py:115` already does).
- **Not in `session_skip_paths`** (`config.py:61-70`) — session middleware would set a cookie on a machine-to-machine call.
- No body-size / rate limit on a new public endpoint.

**Fix:** mandate the `svix` library (or explicit HMAC scheme), add `resend_webhook_secret: SecretStr`, specify replay rejection, raw-body verification, skip-path registration.
_Evidence: design.md Decision 15; email-deliverability/spec.md; config.py:41-70; auth.py:115_

---

## 🟠 High — should resolve

### 6. request_id correlation lost in background tasks
`RequestIdMiddleware` resets `request_id_var` in a `finally` when `call_next` returns; Starlette runs `BackgroundTasks` after that, so email logs carry an empty `request_id`. A failed send can't be traced to its request.
**Fix:** explicitly bind `order_id` + `event` on all email logs / `order_emails` rows (the task already receives them), or pass `request_id` as a task argument. Add a `capture_logs()` test asserting the bound fields.
_Evidence: request_id.py:43-49; logging_config.py:19; precedent test_order_service.py:750_

### 7. PII in logs with no redaction pattern
Console provider logs full recipient + name + shipping address + order contents to structlog → JSON to stdout in prod. No PII-redaction processor exists (`logging_config.py`), and `sanitize.py` only HTML-escapes. This PII sink outlives the DB and is not covered by any erasure process, contradicting the project's GDPR stance.
**Fix:** scope log redaction/retention — log a recipient hash or truncated address; never the body in production.
_Evidence: email-service/spec.md console scenario; logging_config.py:26-27; core-ecommerce/design.md:420_

### 8. New PII stores outside the GDPR deletion story
`order_emails.recipient` (append-only, "indefinite") and any `suppressed_emails` store hold email addresses. Existing erasure anonymizes by `user_id`; anonymous checkouts have no `user_id`, so nothing scrubs these → un-erasable PII by construction. Never mentioned in the design.
**Fix:** specify how both tables are anonymized/retained on erasure.
_Evidence: archive/.../gdpr-deletion/spec.md; core-ecommerce/design.md:420_

### 9. `TRACKING_REQUIRED` (422) cannot come from the Pydantic layer
A `model_validator` raises `RequestValidationError` → the framework's validation envelope, **not** `{"error":{"code":"TRACKING_REQUIRED"}}`. The conditional (required only when `status=="shipped"`) must live in the service/route and raise a custom exception translated inline (like `InvalidStateTransitionError` at `admin.py:420-434`). Also `update_status(conn, order_id, new_status)` (`order_service.py:446`) has **no tracking parameters** and its `UPDATE` writes only `status` — signature + UPDATE must be extended.
**Fix:** add a custom exception + handler; extend `update_status` signature; disambiguate tasks 3.1/3.2/3.3.
_Evidence: order_service.py:446-467; admin.py:420-434; order-tracking/spec.md:26-34_

### 10. Jinja2 autoescape + unsanitized order fields
Renderer never states `autoescape=False`; for `.txt` this is required (else `Ben & Co` → `Ben &amp; Co`, and `<>"'` corrupt the body). `customer_name`/`shipping_address` are inserted raw (unlike comments, which use `sanitize_text`) — safe for plain text, but a latent email-client XSS/spoofing vector the moment the deferred HTML/multipart templates land. Also state explicitly that user values never flow into `Subject`/`From`/`Reply-To` (header injection).
**Fix:** mandate `autoescape=False` now (and on when HTML is added); record a sanitization decision for template inputs.
_Evidence: tasks.md 5.1; design.md Decision 3; comment_service.py:120-121_

---

## 🟡 Cleanup / scope

- **11. task 11.4 is a no-op** — `CreateOrderRequest.customer_email` is already `EmailStr` (`models/orders.py:46`) with `email-validator` in deps. Downgrade to optional typo/MX check or drop.
- **12. Config diverges 3 ways** — `config.py:41` ships `orders@example.invalid`, design.md:220 says `orders@ateliermarie.com`, deliverability spec mandates a subdomain (`orders@send.…`). Reconcile; addresses are bare `str` (consider `EmailStr`), keys are plain `str` (consider `SecretStr` for `email_api_key`, webhook secret, `jwt_secret`, `admin_api_key`).
- **13. `mock-api.ts` not updated** — no `tracking_*` fields / no ship-with-tracking handling (`mock-api.ts:141,268`); breaks the dual mock/real pattern, so the new UI can't be exercised in mock mode. Add a task.
- **14. Template `.txt` packaging** — `[tool.setuptools.packages.find]` discovers Python packages only; `.txt` under `app/email/templates/` isn't package-data, so `FileSystemLoader` finds nothing if the app is ever built/installed. Document the source-checkout (uvicorn) assumption or add `package-data`/`MANIFEST.in`.
- **15. Carrier patterns location contradiction** — design says "stored as config" (design.md:178), tasks say `order_service.py` *or* `utils/carriers.py` (2.2). They're static code used by service + validation + frontend dropdown → belong in `app/constants.py`, not pydantic Settings. Pin one home.
- **16. ⚑ Scope too large** — two reviewers flagged this. Deliverability (webhook route family + suppression store + validation + idempotency + Cyrillic + DMARC ops) is separable from the notification core (service, provider abstraction, templates, BackgroundTasks, tracking schema/API/UI). Recommend splitting deliverability/webhooks into a follow-up change so the core ships and reviews independently.
- **17. Audit table has no query surface; runbook references a non-existent feature** — Migration Plan step 5 says "send test email via admin dashboard," but no task builds a test-send or a read endpoint. Add a minimal `GET /v1/admin/orders/{id}/emails` (delivers the promised auditability) or remove the runbook step.
- **18. `order_emails` loses in-flight sends on shutdown** — a deploy/crash between response and task means no row is written at all (not even "failed"), so the audit table can't distinguish "never attempted" from "sent but unlogged." Write a `pending`/`queued` row before dispatch, or document as accepted risk.
  > ✅ **RESOLVED (2026-07-19) by design Decision 25.** The durable outbox writes the `queued` row **in the same transaction as the order**, before any send — so a crash/deploy/OOM can no longer lose the email or the row; the sweeper resumes it on restart. This is the "write a `queued` row before dispatch" option, adopted as the delivery model rather than an accepted risk.
- **19. Missing test coverage** — both-templates-missing (skip + error log) and provider-raises (swallow, `failed` row, order unaffected) are speced but not tasked; webhook tests omit replay, malformed-but-signed payloads, unknown/duplicate events.
- **20. `order_emails.status` conflates two "skipped" reasons** — idempotency-skip vs suppression-skip share one value; add a `reason`/`detail` column.
- **21. Consider a `RecordingProvider` test double** — asserting rendered content (subject/body, Cyrillic MIME, absence of `List-Unsubscribe`) via captured log strings is brittle; the `EmailProvider` Protocol makes an in-memory recorder trivial. Keep log-capture for the failure paths.

---

## ✅ Confirmed clean (no action)

- **Layer 1/2 boundary** not violated — `app/email/` + `email_service.py` are Layer 1, no imports from `app/analytics/` or `app/ml/`. Fire-and-forget keeps email off the checkout critical path (as fail-safe as Layer 2 without being Layer 2).
- **Admin authz** — `admin_update_order_status` and the whole admin router are gated by `require_admin` (`admin.py:51,407`); triggering emails / setting tracking is admin-only.
- **Locale-from-order** — well-specified, with an explicit admin-locale-differs test (task 7.10).
- **BackgroundTasks run under the async test client** (httpx `ASGITransport` drives the full ASGI cycle), so task 8.6's approach is viable.

### ⚠️ One rationale in design.md is wrong
Decision 3's caveat claims a captured-connection bug "would pass in TestClient but fail in production." Not true here: routes use an inline `with get_db() as conn:` (`orders.py:57`, `admin.py:413`) that commits and closes when the route returns — strictly before background tasks run, in tests too (async client drives the full cycle). A captured-conn bug fails in tests as well. Still open a fresh connection in the task — but fix the stated reason. `get_db()` opens a new `sqlite3.connect` per call (`database.py:411`), so a background-thread read is safe.

---

## Corrections to already-written artifacts (this session)

_Status: ✅ APPLIED (2026-07-15). All blockers 1–5 and high gaps 6–10 folded into design.md / specs / tasks.md. Only the physical scope-split (item 9 below) is deferred pending confirmation of the boundary — captured as a note in proposal.md Scope._

1. **design.md Decision 11 DDL** → ✅ added partial `UNIQUE(order_id, event) WHERE status='sent'`, a `reason` column, and an `order_email_send_claims` table; `status` now has `skipped_duplicate`/`skipped_in_flight`/`skipped_suppressed` (gaps 2, 20).
2. **design.md Decision 11 rationale + email-service/spec.md scenario** → ✅ rewritten to concurrent-send (the toggle transition is impossible) (gap 3).
3. **design.md migration wording + proposal.md** → ✅ replaced "ADD COLUMN IF NOT EXISTS" with `_add_column_if_missing` via `_migrate_existing_schema` + `_SCHEMA_SQL` (gap 4).
4. **email-deliverability/spec.md webhook requirement** → ✅ Svix scheme, `resend_webhook_secret`, replay + raw-body + constant-time + skip-path, duplicate-idempotent (gap 5).
5. **`EmailEvent` + `STATUS_TO_EMAIL_EVENT` map** → ✅ design Decision 19 + tasks 1.5 / 8.2 (`event="placed"`) (gap 1).
6. **design.md Decision 3 caveat** → ✅ corrected the tests-vs-prod rationale (clean section).
7. **tasks.md 11.4** → ✅ downgraded (already satisfied by `EmailStr`) (gap 11).
8. **GDPR/PII coverage** → ✅ design Decision 23 + tasks 12.2/12.3 (gaps 7, 8).
9. **Split deliverability/webhooks** → ⏳ recommended note added to proposal.md Scope; physical split deferred pending confirmation (gap 16).

Also applied: Decision 20 (autoescape + sanitization, gap 10), Decision 21 (`TRACKING_REQUIRED` service-layer, gap 9), Decision 22 (order_id+event log correlation, gap 6), tasks for mock-api parity (9.4), audit read endpoint (12.1), packaging/docs (12.4), and expanded test coverage (5.4, 7.5, 7.10, 11.7).
