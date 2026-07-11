## 1. Backend: Contact Endpoint & Email

- [ ] 1.1 Add SMTP config fields to `app/config.py` (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `CONTACT_EMAIL`) and `INSTAGRAM_URL`
- [ ] 1.2 Create `contact_messages` table in `app/database.py` schema (id, name, email, message, ip_address, created_at, email_sent)
- [ ] 1.3 Create Pydantic models in `app/models/contact.py` (ContactRequest with honeypot field, ContactResponse)
- [ ] 1.4 Create `app/services/contact_service.py` — persist message, send email via aiosmtplib, handle failures gracefully
- [ ] 1.5 Create `app/services/email_service.py` — async SMTP send with timeout and error handling
- [ ] 1.6 Create `app/routes/contact.py` — `POST /v1/contact` with rate limiting (5/hour/IP), honeypot check, validation
- [ ] 1.7 Register contact router in `app/main.py`
- [ ] 1.8 Add `aiosmtplib` to project dependencies

## 2. Backend: Tests

- [ ] 2.1 Write service tests for `contact_service` — persist, email success, email failure (message still saved)
- [ ] 2.2 Write route tests — valid submission (201), missing fields (422), invalid email (422), rate limit (429), honeypot bypass
- [ ] 2.3 Write email service tests — mock SMTP, verify correct headers and body

## 3. Frontend: Instagram Link in Footer

- [ ] 3.1 Add `NEXT_PUBLIC_INSTAGRAM_URL` to environment config and `.env.example`
- [ ] 3.2 Add Instagram SVG icon component (or use existing icon approach)
- [ ] 3.3 Update Footer component — add Instagram icon link with `target="_blank"`, `rel="noopener noreferrer"`, `aria-label="Follow us on Instagram"`, hover color transition to gold

## 4. Frontend: Contact Page

- [ ] 4.1 Create `/contact` page (`app/contact/page.tsx`) with heading, intro text, and form layout
- [ ] 4.2 Create `ContactForm` client component with name, email, message fields + hidden honeypot field
- [ ] 4.3 Add client-side validation (required fields, email format) with inline error messages
- [ ] 4.4 Implement form submission to `POST /v1/contact` with loading state, success message, and error handling
- [ ] 4.5 Style the contact page with luxury design system (spacing, typography, gold accents)
- [ ] 4.6 Add Contact form to mock API (`lib/mock-api.ts`) for development without backend

## 5. Frontend: Footer Update

- [ ] 5.1 Replace footer "Contact" placeholder link (`#`) with working `/contact` link
- [ ] 5.2 Add social media section to footer layout (visually separated from nav links)
- [ ] 5.3 Verify responsive behavior — icon touch targets, layout on mobile/tablet/desktop

## 6. Integration & Verification

- [ ] 6.1 End-to-end test: submit contact form → message persisted → email received (dev SMTP)
- [ ] 6.2 Verify rate limiting works across multiple rapid submissions
- [ ] 6.3 Verify honeypot silently discards bot submissions
- [ ] 6.4 Verify Layer 2 boundary — contact feature is Layer 1 (no analytics dependencies)
