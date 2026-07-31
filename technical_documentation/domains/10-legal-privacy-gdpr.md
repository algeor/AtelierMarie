# Legal, Privacy, Cookies, And GDPR

This project sells real goods. Legal surfaces are part of the product, not decoration.

## Main Files

- `app/legal.py`
- `app/services/gdpr_service.py`
- `app/services/analytics_service.py`
- `frontend/app/[locale]/terms/page.tsx`
- `frontend/app/[locale]/privacy/page.tsx`
- `frontend/app/[locale]/cookies/page.tsx`
- `frontend/lib/legal.ts`
- `frontend/components/layout/Footer.tsx`
- `frontend/components/layout/CookieSettingsButton.tsx`
- `frontend/contexts/CookieConsentContext.tsx`
- `app/email/templates/*`

## Legal Identity

`app/legal.py` centralizes trader identity values used by email/templates/pages.

Do not copy/paste legal identity into random files if a shared source exists.

## Required Storefront Surfaces

- Terms and returns page.
- Privacy page.
- Cookie page.
- Footer links.
- Checkout disclosure.
- Order confirmation policy references.
- Email policy references.
- Product safety/responsible-party info on product offers.
- Contact form privacy notice.

## Product Safety

Product safety fields live on product records.

Rules:

- Safety warnings must be visible on product detail.
- Care instructions should be visible where useful.
- Responsible-party information should not be hidden only in FAQ.
- Admin product form should preserve safety fields.

## Cookie And Analytics Consent

Consent is both frontend and backend state.

Frontend:

- shows consent UI
- stores preference
- gates tracking calls

Backend:

- records current consent version by session
- only accepts/records events when consent is verified

Production guard:

- analytics cannot be enabled in production without legal approval config.

## GDPR Current Helpers

Current helper coverage includes:

- anonymizing order email recipient for an order
- aging out suppressed emails
- anonymizing analytics subject data

The active erasure spec describes a fuller intended flow. Do not assume it is fully implemented without checking code.

## Erasure Design Direction

When full erasure is implemented, the intended behavior is:

- Resolve by email/user/session where appropriate.
- Scrub order PII but preserve financial/order records inside retention period.
- Delete comments because bodies may contain PII.
- Scrub users with unique placeholders because email/google id are unique and not null.
- Keep suppression records to avoid re-contact.
- Hard-delete retained records only after legal retention window.

## Safe Change Checklist

- Legal links still reachable from footer and checkout.
- Cookie page accurately describes analytics state.
- Product detail still shows safety fields.
- Email templates include relevant policy URLs.
- Erasure/anonymization does not destroy required financial audit data.
- Suppression remains effective.

