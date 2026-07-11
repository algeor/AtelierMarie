## Why

The website currently lacks any way for visitors to connect with Atelier Marie outside of placing an order. An Instagram link drives social engagement and builds brand trust (especially important for a luxury/artisanal product). A contact form gives customers a frictionless way to ask questions about products, custom orders, or shipping — without needing to find or copy an email address.

## What Changes

- Add an **Instagram button** (icon link) visible site-wide in the footer that opens the Atelier Marie Instagram profile in a new tab.
- Add a **Contact Us page** (`/contact`) with a simple form (name, email, message) that sends the submission to the shop owner's email address.
- Add a "Contact" navigation link in the footer (replacing the current `#` placeholder).

## Capabilities

### New Capabilities
- `contact-form`: A contact page with a form that collects name, email, and message, validates inputs, and delivers the submission to the owner via email.
- `social-links`: An Instagram icon button in the footer linking to the atelier's Instagram profile.

### Modified Capabilities
- `global-layout`: Footer gains a working Contact link (replacing `#` placeholder) and an Instagram social icon.

## Impact

- **Frontend:** New `/contact` page, updated footer component (icon + link).
- **Backend:** New `POST /v1/contact` endpoint to receive form submissions and trigger email delivery.
- **Dependencies:** Email delivery mechanism (SMTP or transactional email service).
- **Existing code:** Footer component updated (minor — replaces placeholder link, adds icon).
