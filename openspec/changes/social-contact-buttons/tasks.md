## 0. Dependency: Shared Email Architecture

- [ ] 0.1 Confirm `email-notifications` shared email configuration, provider factory, template renderer, and `app/services/email_service.py` orchestration are implemented or implement the shared pieces first

## 1. Backend: Contact Endpoint & Email

- [ ] 1.1 Reuse shared email settings from `email-notifications` (`email_provider`, `email_api_key`, `email_from_address`, `email_from_name`, `email_reply_to`, `admin_notification_email`)
- [ ] 1.2 Create `contact_messages` table in `app/database.py` schema (id, name, email, message, ip_address, created_at, email_sent)
- [ ] 1.3 Create Pydantic models in `app/models/contact.py` (ContactRequest with honeypot field, ContactResponse)
- [ ] 1.4 Create `app/services/contact_service.py` — persist message first, expose helper to mark `email_sent` after provider success
- [ ] 1.5 Extend shared `app/services/email_service.py` with `send_contact_message(message_id)` using the shared provider factory and `contact_message` template
- [ ] 1.6 Create `app/routes/contact.py` — `POST /v1/contact` with `BackgroundTasks`, rate limiting (5/hour/IP), honeypot check, validation, and background contact email enqueue
- [ ] 1.7 Register contact router in `app/main.py`
- [ ] 1.8 Add contact email templates under `app/email/templates/en/contact_message.txt` and `app/email/templates/bg/contact_message.txt`

## 2. Backend: Tests

- [ ] 2.1 Write service tests for `contact_service` — persist, mark email sent, email failure leaves message saved
- [ ] 2.2 Write route tests — valid submission (201 + background task queued), missing fields (422), invalid email (422), rate limit (429), honeypot bypass
- [ ] 2.3 Write email service tests — mock shared provider, verify template context, recipient, reply-to, tags, and `email_sent` update

## 3. Frontend: Social Links in Footer

- [ ] 3.1 Add `NEXT_PUBLIC_INSTAGRAM_URL` and `NEXT_PUBLIC_TIKTOK_URL` to frontend environment config and `.env.local.example`
- [ ] 3.2 Add Instagram and TikTok SVG icon components (or use existing icon approach)
- [ ] 3.3 Update Footer component — add Instagram and TikTok icon links with `target="_blank"`, `rel="noopener noreferrer"`, accessible labels, and hover color transition to gold

## 4. Frontend: Contact Page

- [ ] 4.1 Create localized `/contact` page (`app/[locale]/contact/page.tsx`) with heading, intro text, and form layout
- [ ] 4.2 Create `ContactForm` client component with name, email, personalized message fields + hidden honeypot field
- [ ] 4.3 Add client-side validation (required fields, email format) with inline error messages
- [ ] 4.4 Implement form submission to `POST /v1/contact` with loading state, success message, and error handling
- [ ] 4.5 Style the contact page with luxury design system (spacing, typography, gold accents)
- [ ] 4.6 Add Contact form to mock API (`lib/mock-api.ts`) for development without backend

## 5. Frontend: Footer Update

- [ ] 5.1 Replace footer "Contact" placeholder link (`#`) with working `/contact` link
- [ ] 5.2 Add Instagram/TikTok social media section to footer layout (visually separated from nav links)
- [ ] 5.3 Verify responsive behavior — icon touch targets, layout on mobile/tablet/desktop

## 6. Integration & Verification

- [ ] 6.1 End-to-end test: submit contact form → message persisted → contact email queued/sent through shared console or Resend provider
- [ ] 6.2 Verify rate limiting works across multiple rapid submissions
- [ ] 6.3 Verify honeypot silently discards bot submissions
- [ ] 6.4 Verify Layer 2 boundary — contact feature is Layer 1 (no analytics dependencies)
