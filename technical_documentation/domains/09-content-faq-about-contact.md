# Content: FAQ, Atelier Story, Contact, Banner

These features let the owner manage trust-building content without changing code.

## FAQ

Main files:

- `app/services/faq_service.py`
- `app/routes/faq.py`
- `app/models/faq.py`
- `frontend/components/faq/FaqAccordion.tsx`
- `frontend/components/admin/FaqManager.tsx`
- `frontend/app/[locale]/faq/page.tsx`
- `frontend/app/[locale]/admin/faq/page.tsx`

How it works:

```text
Admin edits sections/items
  -> FAQ service stores bilingual text
  -> public endpoint returns published localized sections/items
  -> FAQ accordion renders page
```

Rules:

- Section slugs are stable anchors.
- English is required, Bulgarian can fallback.
- Items can be published/unpublished.
- Ordering is controlled by `sort_order`.

## Atelier Story / About

Main files:

- `app/services/about_service.py`
- `app/routes/about.py`
- `app/models/about.py`
- `frontend/components/atelier/*`
- `frontend/components/admin/AtelierAdminManager.tsx`
- `frontend/app/[locale]/atelier/page.tsx`
- `frontend/app/[locale]/admin/atelier/page.tsx`

How it works:

```text
about_sections define fixed section slugs/types
  -> admin edits text, CTA, images, publish state, order
  -> about_items add cards/timeline/etc under sections
  -> public endpoint resolves localized published content
  -> frontend renders sections by type
```

Rules:

- Slug and type are not casual admin-editable fields.
- Text is sanitized on write and unsanitized for display.
- URLs must be safe HTTP(S) or safe relative URLs.
- Images reuse image processing pipeline with owner-specific pseudo product slugs.

## Contact Form

Main files:

- `app/models/contact.py`
- `app/routes/contact.py`
- `app/services/contact_service.py`
- `frontend/components/contact/ContactForm.tsx`
- `frontend/app/[locale]/contact/page.tsx`

How it works:

```text
customer submits form
  -> honeypot checked
  -> IP rate limit checked
  -> contact_messages row inserted queued
  -> background email worker notifies owner
  -> old messages cleaned by retention
```

Rules:

- Honeypot submissions return accepted-style result but are not stored.
- Rate limit is per IP per hour.
- Admin notification email must be configured to send.

## Banner

Main files:

- `app/services/banner_service.py`
- `app/routes/promotions.py`
- `frontend/components/layout/AnnouncementBar.tsx`

How it works:

- Admin sets bilingual message/link/schedule/enabled.
- Public route returns visible banner.
- `version` changes dismissal identity.

## Safe Change Checklist

- Content is bilingual or has clear fallback.
- Free text is sanitized.
- Publish toggles work.
- Reorder rejects missing/extra IDs where applicable.
- Contact email failure does not fail form submission after accepted DB write.
- Legal/privacy notices remain visible on contact form.

