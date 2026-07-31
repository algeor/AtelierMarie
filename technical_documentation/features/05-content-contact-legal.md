# Content, Contact, Legal, And GDPR

Use this when touching FAQ, atelier/about story, contact form, social links, legal pages, product safety, privacy/cookies, or data erasure.

## Content Areas

The storefront has editable/support content, not only products:

- FAQ page and admin manager
- Atelier/about story page and admin manager
- Contact page/form
- Social links in footer
- Terms page
- Privacy page
- Cookies page
- Product safety and responsible-party info

## Main Backend Files

- `app/routes/faq.py`, `app/services/faq_service.py`, `app/models/faq.py`
- `app/routes/about.py`, `app/services/about_service.py`, `app/models/about.py`
- `app/routes/contact.py`, `app/services/contact_service.py`, `app/models/contact.py`
- `app/legal.py`: public trader/legal identity values.
- `app/services/gdpr_service.py`: current GDPR helper functions.
- `app/services/analytics_service.py`: analytics subject anonymization.
- `app/email/templates/*`: legal/email copy hooks.

## Main Frontend Files

- `frontend/app/[locale]/faq/page.tsx`
- `frontend/components/faq/FaqAccordion.tsx`
- `frontend/components/admin/FaqManager.tsx`
- `frontend/app/[locale]/atelier/page.tsx`
- `frontend/components/atelier/*`
- `frontend/components/admin/AtelierAdminManager.tsx`
- `frontend/app/[locale]/contact/page.tsx`
- `frontend/components/contact/ContactForm.tsx`
- `frontend/app/[locale]/terms/page.tsx`
- `frontend/app/[locale]/privacy/page.tsx`
- `frontend/app/[locale]/cookies/page.tsx`
- `frontend/components/layout/Footer.tsx`
- `frontend/messages/en.json`, `frontend/messages/bg.json`

## FAQ Rules

- Public FAQ is localized and grouped into sections.
- Admin can create/update/delete/reorder/publish items.
- Product detail can link to relevant FAQ help.
- Avoid hardcoding FAQ text into product pages.

## Atelier Story Rules

- About content is section-based.
- Sections and items support bilingual text.
- Public sections render by section type.
- Admin can edit text, images, ordering, and publish toggles.
- Image uploads reuse existing image pipeline patterns.
- Text is sanitized on write.

## Contact Rules

- Contact submissions persist accepted messages.
- Spam controls include honeypot/rate style protections.
- Contact notifications use durable email delivery.
- Contact form must include privacy notice copy.
- Contact message retention is configured.

## Legal Rules

- Terms, privacy, and cookie pages must be reachable from footer and checkout where relevant.
- Checkout must disclose legal/privacy/terms information before purchase.
- Order confirmation and emails include policy references where required.
- Product detail must show candle safety and responsible-party information. Do not hide safety only in FAQ.
- Legal text is not a marketing toy. Keep it clear and accurate.

## GDPR / Erasure Rules

Current implemented helper coverage includes order email anonymization, suppressed email age-out, and analytics subject anonymization. The active GDPR erasure spec describes the fuller intended behavior:

- Resolve a subject by email, user ID, and optionally session ID.
- Scrub order PII while preserving financial/order structure inside retention windows.
- Delete comments because comment body can contain PII.
- Scrub users with unique placeholders because email/google ID are unique and not null.
- Keep suppression entries so the shop does not accidentally re-contact someone.
- Hard-delete old retained records only after the configured retention window.

If you implement more erasure behavior, read the active `openspec/changes/gdpr-data-erasure` docs first.

## Safe Change Checklist

- Updated both languages.
- Sanitized admin-entered rich/free text.
- Kept legal links discoverable but not shouty.
- Did not remove safety/responsible-party info from product offers.
- Contact form still stores and emails through durable paths.
- Erasure changes preserve order financial data when legally required.

