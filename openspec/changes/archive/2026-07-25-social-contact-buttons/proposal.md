## Why

Visitors currently have no clear way to reach Atelier Marie outside the checkout flow. The footer also contains a placeholder Contact link, so the site advertises a path that does not work. For a small handmade-products shop, the useful version is simple: visible social links, a real contact page, and reliable owner notification when someone asks about custom work, shipping, or an order.

## What Changes

- Add Instagram and TikTok icon links in the site-wide footer.
- Replace the footer Contact placeholder with a localized Contact page route.
- Add a localized contact page with a form for name, email, and message.
- Add `POST /v1/contact` to validate and persist submissions.
- Queue the owner notification through the durable email subsystem from `email-notifications`; contact mail uses the same ZeptoMail/console providers and the same `ADMIN_NOTIFICATION_EMAIL` (`contacts@theateliermarie.com`).

## Decisions

- Instagram URL: `https://www.instagram.com/atelier_marie25?igsh=MWQ1YzA4aHF2a3Q4MA==`
- TikTok URL: `https://www.tiktok.com/@ateliermarie25?_r=1&_t=ZN-98H9buODbdu`
- Owner recipient: reuse `ADMIN_NOTIFICATION_EMAIL`; do not add `CONTACT_NOTIFICATION_EMAIL`.
- Delivery: no FastAPI `BackgroundTasks`; contact notifications are durable outbox work so a process restart does not lose the email intent.
- Scope: no CRM, no chat widget, no social feed embed, and no admin message-management UI in this change.

## Capabilities

### New Capabilities

- `contact-form`: Localized contact page, validated submission endpoint, persisted contact messages, spam controls, and durable owner notification.
- `social-links`: Instagram and TikTok icon links in the footer.

### Modified Capabilities

- `global-layout`: Footer gains a working Contact link and social icon links.

## Impact

- **Frontend:** Add `app/[locale]/contact/page.tsx`, a client contact form component, message strings, API facade method, mock API support, and footer social links.
- **Backend:** Add contact models, route, service, database table(s), email template(s), and a contact-email drain path integrated with the existing email provider/rendering stack.
- **Email:** Reuses the `email-integration` branch's durable outbox concepts and ZeptoMail/console providers; does not misuse order-specific `order_emails` rows for contact messages.
- **Configuration:** Add public frontend social URL env vars with the confirmed Atelier Marie URLs as defaults. Backend recipient remains `ADMIN_NOTIFICATION_EMAIL`.
