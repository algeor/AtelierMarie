## 0. Dependency Alignment

- [x] 0.1 Confirm the `email-integration` / `email-notifications` email foundation is present before implementation: provider factory, console provider, ZeptoMail provider, Jinja2 renderer, and email outbox loop in app lifespan.
- [x] 0.2 Confirm the existing order-specific `order_emails` table is not reused for contact messages; contact delivery needs its own contact-shaped durable queue state.

## 1. Backend: Contact Persistence and Models

- [x] 1.1 Add `contact_messages` schema to `app/database.py` with message fields plus email delivery state (`email_status`, attempts, next attempt, claim expiry, sent timestamp, error) and indexes for created-at/status.
- [x] 1.2 Add idempotent migration support for existing SQLite DBs if the table is missing.
- [x] 1.3 Create `app/models/contact.py` with `ContactRequest` (`name`, `email`, `message`, `locale`, hidden `website`) and `ContactResponse` (`status`, `message_id` optional).
- [x] 1.4 Apply server-side validation: trim strings, require non-empty name/message, validate email via `EmailStr`, restrict locale to `en|bg`, and enforce reasonable max lengths.
- [x] 1.5 Create `app/services/contact_service.py` to persist valid messages and expose the contact email drain/send helpers.

## 2. Backend: Contact Route and Spam Controls

- [x] 2.1 Create `app/routes/contact.py` with `POST /v1/contact`.
- [x] 2.2 Reject non-JSON submissions consistently with existing state-changing routes.
- [x] 2.3 Implement honeypot behavior: non-empty `website` returns HTTP 201 success but does not persist or queue email.
- [x] 2.4 Implement SQLite-backed rate limiting: max 5 accepted submissions per IP per rolling hour; return HTTP 429 with a user-safe error when exceeded.
- [x] 2.5 Persist the message with `email_status='queued'` in the same DB transaction that accepts the request.
- [x] 2.6 Register the contact router in `app/main.py` at `/v1/contact`.

## 3. Backend: Durable Contact Email Delivery

- [x] 3.1 Add `contact_message.txt` Jinja2 templates under `app/email/templates/en/` and `app/email/templates/bg/`.
- [x] 3.2 Build contact email context from the `contact_messages` row: submitter name, submitter email, message body, locale, created timestamp, and message id.
- [x] 3.3 Send contact notifications to `settings.admin_notification_email`; if unset, mark the row skipped/no-recipient or failed-permanent and log the reason without failing the visitor submission.
- [x] 3.4 Send with `reply_to` set to the submitter's email address so the owner can reply directly.
- [x] 3.5 Implement `drain_contact_message_emails()` with retry/backoff semantics matching the order email outbox.
- [x] 3.6 Claim contact rows before sending (`queued`/`failed` -> `in_flight` with claim expiry) so multiple uvicorn workers cannot send duplicate owner notifications.
- [x] 3.7 Integrate contact draining into the existing email outbox loop tick; avoid a second long-running app task unless the existing loop cannot be cleanly reused.
- [x] 3.8 Ensure logs redact submitter email and never log full message bodies in production.

## 4. Backend Tests

- [x] 4.1 Service tests: valid contact persists as queued, honeypot is ignored, rate limit counts recent messages, and max-length validation rejects oversized input.
- [x] 4.2 Route tests: 201 valid response, 422 missing/invalid fields, 429 rate limit, non-JSON rejection, and honeypot fake-success.
- [x] 4.3 Email drain tests with a recording provider: queued row sends to `ADMIN_NOTIFICATION_EMAIL`, `reply_to` equals submitter email, row becomes sent, and provider failures retry/terminally fail as expected.
- [x] 4.4 Concurrency test: two concurrent contact drains for the same queued row produce at most one provider send.
- [x] 4.5 Template tests: EN/BG contact templates render subject/body with submitter details and message body.

## 5. Frontend: Social Links in Footer

- [x] 5.1 Add `NEXT_PUBLIC_INSTAGRAM_URL` and `NEXT_PUBLIC_TIKTOK_URL` to `frontend/.env.local.example` with the confirmed Atelier Marie profile URLs.
- [x] 5.2 Add a small frontend config/helper for social URLs with defaults matching the confirmed URLs.
- [x] 5.3 Add Instagram and TikTok inline SVG icon components (no new icon dependency required) or use an existing local icon pattern if one exists by implementation time.
- [x] 5.4 Update `Footer` to render Instagram/TikTok icon links with `target="_blank"`, `rel="noopener noreferrer"`, descriptive `aria-label`s, visible focus states, and 44x44px touch targets.
- [x] 5.5 Replace the Contact footer placeholder with the localized `Link href="/contact"`; leave unrelated footer placeholders (such as About) unchanged unless a separate change covers them.

## 6. Frontend: Contact Page and Form

- [x] 6.1 Add `app/[locale]/contact/page.tsx` with localized page metadata and restrained storefront styling.
- [x] 6.2 Build the contact page as a restrained two-column desktop layout with short contextual copy plus direct email/social links beside the form; stack cleanly on mobile.
- [x] 6.3 Add a `ContactForm` client component with name, email, message, hidden `website`, loading state, success state, and non-destructive error state.
- [x] 6.4 Style the form using existing storefront conventions: modest heading scale, calm borders, clear focus rings, readable inline errors, and the existing primary button treatment.
- [x] 6.5 Add client-side validation matching backend basics: required fields, email format, max lengths, and inline accessible errors.
- [x] 6.6 Add `contact` messages to `frontend/messages/en.json` and `frontend/messages/bg.json`.
- [x] 6.7 Add TypeScript request/response types and an API facade method that calls `POST /v1/contact`.
- [x] 6.8 Add mock API support for contact submission so mock-mode development remains usable.

## 7. Frontend Tests

- [x] 7.1 Footer tests: Contact link points to `/contact`; Instagram/TikTok links render with confirmed URLs, new-tab/security attributes, and accessible labels.
- [x] 7.2 Contact form tests: required/email validation, successful submission clears the form and shows success, backend error preserves entered data, and loading state prevents duplicate submits.
- [x] 7.3 i18n rendering tests for English and Bulgarian contact page/form labels and messages.
- [x] 7.4 Responsive presentation tests or screenshots: desktop uses the two-column layout, mobile stacks cleanly, and no text/control overlap appears in the contact page or footer.

## 8. Integration Verification

- [x] 8.1 End-to-end backend flow: submit contact form -> row persisted as queued -> one sweeper tick sends via console/recording provider -> row marked sent.
- [x] 8.2 Verify provider outage does not fail the visitor response and the contact row remains retryable.
- [x] 8.3 Verify `/contact` redirects through existing locale middleware and `/{locale}/contact` renders for both `en` and `bg`.
- [x] 8.4 Verify social links work in desktop and mobile footer layouts.
