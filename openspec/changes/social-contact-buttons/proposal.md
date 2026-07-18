## Why

The website currently lacks any way for visitors to connect with Atelier Marie outside of placing an order. Instagram and TikTok links drive social engagement and build brand trust (especially important for a luxury/artisanal product). A contact form gives customers a frictionless way to ask questions about products, custom orders, shipping, or personalized requests — without needing to find or copy an email address.

## What Changes

- Add **Instagram and TikTok buttons** (icon links) visible site-wide in the footer that open the Atelier Marie social profiles in new tabs.
- Add a **Contact Us page** (`/contact`) with a simple form (name, email, personalized message) that stores the submission and notifies the shop owner through the shared email-notifications delivery architecture.
- Add a "Contact" navigation link in the footer (replacing the current `#` placeholder).

## Capabilities

### New Capabilities
- `contact-form`: A contact page with a form that collects name, email, and a personalized message, validates inputs, persists the submission, and delivers the owner notification through the shared email provider architecture.
- `social-links`: Instagram and TikTok icon buttons in the footer linking to the atelier's social profiles.

### Modified Capabilities
- `global-layout`: Footer gains a working Contact link (replacing `#` placeholder) and Instagram/TikTok social icons.

## Impact

- **Frontend:** New `/contact` page, updated footer component (Contact link + Instagram/TikTok icon links).
- **Backend:** New `POST /v1/contact` endpoint to receive form submissions, persist them, and enqueue owner email notification through the shared email service.
- **Dependencies:** Reuses the `email-notifications` email provider architecture (console provider for dev/test, Resend provider for production, Jinja2 templates).
- **Existing code:** Footer component updated (minor — replaces placeholder link, adds icon).
