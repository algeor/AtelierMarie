## Context

Atelier Marie's website currently has no social media presence or direct contact mechanism beyond placing an order. The footer already includes a placeholder "Contact" link pointing to `#`. The site uses Next.js 14 (App Router), Tailwind CSS with a luxury design system, and a FastAPI backend. There is no email-sending infrastructure in place yet.

## Goals / Non-Goals

**Goals:**
- Give visitors a one-click path to the Atelier Marie Instagram profile
- Provide a simple, accessible contact form that delivers messages to the owner
- Keep the implementation minimal — this is a small family business, not a ticketing system

**Non-Goals:**
- No CRM, ticket tracking, or reply-from-dashboard functionality
- No real-time chat or chatbot
- No social media feed embed or widget
- No newsletter signup (separate concern)
- No spam protection beyond basic validation (can add reCAPTCHA later if needed)

## Decisions

### 1. Email delivery: SMTP via Python's `smtplib` + `aiosmtplib`

**Rationale:** The owner already has Gmail. Using SMTP with an app password (or environment-configured SMTP credentials) keeps dependencies minimal — no external service signup required. `aiosmtplib` integrates naturally with FastAPI's async model.

**Alternatives considered:**
- *Transactional email service (SendGrid, Resend):* Overkill for <10 messages/day. Adds external dependency and API key management.
- *Save to DB only, no email:* Owner would need to check admin dashboard — easy to miss messages.

**Decision:** Send email via SMTP on form submit. Also persist the message to SQLite as a lightweight audit log (owner can review in admin later if needed).

### 2. Contact form fields: name, email, message only

**Rationale:** Minimizing friction maximizes submissions. Phone number, subject line, and category dropdowns add complexity without value at this scale.

### 3. Instagram link: icon in footer, not header

**Rationale:** The header is reserved for core navigation (Home, Shop, Cart). Social links belong in the footer — this is the standard pattern for e-commerce. Uses the existing footer layout without cluttering primary navigation.

### 4. Rate limiting on contact endpoint

**Rationale:** Open contact forms attract spam bots. A simple per-IP rate limit (5 submissions per hour) provides baseline protection without requiring CAPTCHA — which would hurt the luxury brand feel.

**Implementation:** In-memory dict with IP → timestamp list, cleaned on access. Sufficient for single-server deployment.

### 5. Contact page as a Next.js page, not a modal

**Rationale:** A dedicated `/contact` page is better for SEO, can be linked from anywhere, and gives the form room to breathe. Aligns with the luxury, spacious aesthetic.

## Risks / Trade-offs

- **[SMTP delivery failure]** → Mitigation: Persist message to DB first, then attempt email. If email fails, message is still saved and visible in admin. Log the failure.
- **[Spam submissions]** → Mitigation: Rate limiting (5/hour/IP). Honeypot field (hidden input — bots fill it, humans don't). Can add CAPTCHA in future if needed.
- **[Gmail SMTP limits]** → Gmail allows ~500 emails/day with app passwords. More than sufficient for a small atelier. If volume grows, switch to a transactional service later.
- **[Instagram URL changes]** → Store the Instagram URL in environment config (`INSTAGRAM_URL`) so it's changeable without code deployment.

## Open Questions

- What is the Atelier Marie Instagram handle/URL? (Needed for implementation — can use placeholder for now)
- What email address should receive contact form submissions? (Owner's Gmail, presumably)
