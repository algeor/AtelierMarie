# Routing, Layout, And I18n

The frontend is locale-prefixed and built around `next-intl`.

## URL Shape

Customer/admin pages live under:

```text
/en/...
/bg/...
```

Examples:

- `/en/products`
- `/bg/products/lavender-dream-300ml`
- `/en/admin/orders`

The design-system gallery is outside locale routing.

## Main Files

- `frontend/middleware.ts`: locale detection and redirect.
- `frontend/i18n/routing.ts`: supported locales and default locale.
- `frontend/i18n/navigation.ts`: localized Link/router helpers.
- `frontend/i18n/request.ts`: loads messages for current request locale.
- `frontend/app/[locale]/layout.tsx`: app providers and global layout.
- `frontend/messages/en.json`, `frontend/messages/bg.json`: translations.

## Middleware Behavior

The middleware does three useful things:

1. Redirects unsupported two-letter locale prefixes to `/en/...`.
2. Adds locale prefix when missing.
3. Detects locale from `NEXT_LOCALE` cookie, then `Accept-Language`, then default English.

It excludes:

- API routes
- Next internals
- design-system gallery
- static files

## Locale Layout Provider Stack

`frontend/app/[locale]/layout.tsx` wraps pages like this:

```text
NextIntlClientProvider
  AuthProvider
    CookieConsentProvider
      CartProvider
        AnnouncementBar
        Header
        CartDrawer
        main page content
        Footer
```

Why order matters:

- Auth should be available before cart refreshes triggered by session rotation.
- Consent provider wraps tracking-aware components.
- Cart provider owns drawer and badge used by layout.

## Adding A Page

Add pages under `frontend/app/[locale]/...`.

Then check:

- navigation link if public page
- admin sidebar link if admin page
- messages in both languages
- API facade/mock if page fetches data
- tests for render/empty/error states

## Translation Rules

- Add every user-visible string to both message files.
- Do not hardcode nav labels, buttons, or errors in components.
- Keep keys grouped by feature.
- Use backend error codes for localized display when possible.
- Test Bulgarian layout when text is longer.

## Links

Use localized helpers from `@/i18n/navigation`:

```ts
import { Link, useRouter, usePathname } from "@/i18n/navigation";
```

Avoid raw `next/link` for app pages unless there is a clear reason.

## SEO / Metadata Notes

- Locale pages should set appropriate metadata where needed.
- Product/detail pages should preserve alternate language behavior.
- Legal pages should be discoverable from footer and checkout.

