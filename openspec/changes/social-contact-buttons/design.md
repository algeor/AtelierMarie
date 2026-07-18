## Context

Atelier Marie's website currently has no social media presence or direct contact mechanism beyond placing an order. The footer already includes a placeholder "Contact" link pointing to `#`. The site uses Next.js 14 (App Router), Tailwind CSS with a luxury design system, and a FastAPI backend. Email delivery architecture is owned by the `email-notifications` change (`app/email` provider abstraction, console provider for dev/test, Resend provider for production, Jinja2 templates, and FastAPI `BackgroundTasks`).

## Goals / Non-Goals

**Goals:**
- Give visitors a one-click path to the Atelier Marie Instagram profile and TikTok profile
- Provide a simple, accessible contact form that delivers personalized messages to the owner's email address
- Keep the implementation minimal — this is a small family business, not a ticketing system

**Non-Goals:**
- No CRM, ticket tracking, or reply-from-dashboard functionality
- No real-time chat or chatbot
- No social media feed embed or widget
- No newsletter signup (separate concern)
- No spam protection beyond basic validation (can add reCAPTCHA later if needed)

## Decisions

### 1. Email delivery: reuse shared email provider architecture

**Rationale:** Contact submissions and order notifications are both owner/customer email workflows. They should use the same delivery layer from `email-notifications`: `EmailProvider` Protocol, `ConsoleProvider` for development/tests, `ResendProvider` for production, centralized email settings, and Jinja2 templates. This avoids duplicate SMTP-specific configuration and keeps deliverability behavior consistent across the app.

**Alternatives considered:**
- *Separate SMTP service with `aiosmtplib`:* Rejected because it creates parallel email infrastructure, separate configuration, and different failure semantics from order notifications.
- *Save to DB only, no email:* Owner would need to check admin dashboard — easy to miss messages.

**Decision:** Persist the contact message first, then enqueue a background email notification using the shared `app/services/email_service.py` orchestration and shared provider factory. Contact email should use a dedicated `contact_message` template, send to `ADMIN_NOTIFICATION_EMAIL`, and pass the submitter email as `reply_to` where supported.

### 2. Contact form fields: name, email, message only

**Rationale:** Minimizing friction maximizes submissions. Phone number, subject line, and category dropdowns add complexity without value at this scale.

### 3. Social profile links: icons in footer, not header

**Rationale:** The header is reserved for core navigation (Home, Shop, Cart). Instagram and TikTok links belong in the footer — this is the standard pattern for e-commerce. Uses the existing footer layout without cluttering primary navigation.

### 4. Rate limiting on contact endpoint

**Rationale:** Open contact forms attract spam bots. A simple per-IP rate limit (5 submissions per hour) provides baseline protection without requiring CAPTCHA — which would hurt the luxury brand feel.

**Implementation:** In-memory dict with IP → timestamp list, cleaned on access. Sufficient for single-server deployment.

### 5. Contact page as a Next.js page, not a modal

**Rationale:** A dedicated `/contact` page is better for SEO, can be linked from anywhere, and gives the form room to breathe. Aligns with the luxury, spacious aesthetic.

## Risks / Trade-offs

- **[Email delivery failure]** → Mitigation: Persist message to DB first, then enqueue delivery through the shared email service. If provider/template delivery fails, message is still saved and visible in admin. Log the failure without failing the form submission.
- **[Spam submissions]** → Mitigation: Rate limiting (5/hour/IP). Honeypot field (hidden input — bots fill it, humans don't). Can add CAPTCHA in future if needed.
- **[Resend quota or DNS not configured]** → Console provider works in development/test; production sends depend on the shared Resend configuration from `email-notifications`. Failures are logged and contact submissions remain persisted.
- **[Social profile URL changes]** → Store the Instagram and TikTok URLs in frontend environment config (`NEXT_PUBLIC_INSTAGRAM_URL`, `NEXT_PUBLIC_TIKTOK_URL`) so they are changeable without code deployment.

## Open Questions

- What is the Atelier Marie Instagram handle/URL? (Needed for implementation — can use placeholder for now)
- What is the Atelier Marie TikTok handle/URL? (Needed for implementation — can use placeholder for now)
- Should contact submissions use the same `ADMIN_NOTIFICATION_EMAIL` as order alerts, or a separate future `CONTACT_NOTIFICATION_EMAIL` setting?
