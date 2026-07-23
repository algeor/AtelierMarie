# Bug 001 — `/design-system` gallery is unreachable (redirects to a 404)

**Status:** Fixed (option A applied 2026-07-23)
**Found:** 2026-07-23
**Area:** Frontend / i18n routing
**Severity:** Low (dev-only page, no user impact)

## Summary
The design-system component gallery lives outside the `[locale]` segment, but
the i18n middleware still matches its path and redirects it to a locale-prefixed
URL that has no page — so the gallery 404s.

## Details
- Page file: `frontend/app/design-system/page.tsx` (outside `[locale]/`)
- There is **no** `frontend/app/[locale]/design-system/page.tsx`
- Middleware matcher (`frontend/middleware.ts`):
  `matcher: ["/((?!api|_next|.*\\..*).*)"]` — this matches `/design-system`
  (no file extension, not `api`/`_next`).
- Flow for a request to `/design-system`:
  1. `firstSegment` = `"design-system"` → fails the `^[a-z]{2}$` locale check, skipped.
  2. `hasLocalePrefix("/design-system")` → `false`.
  3. Middleware issues a 307 redirect to `/{locale}/design-system`
     (e.g. `/en/design-system`).
  4. `/en/design-system` maps to no page → **404**.

Net effect: neither `/design-system` nor `/en/design-system` renders the gallery.

## Repro
1. `make dev-frontend`
2. Visit `http://localhost:3000/design-system`
3. Observe redirect to `/en/design-system` and a 404.

## Fix options
- **A (recommended):** Exclude `design-system` from the middleware matcher, e.g.
  `matcher: ["/((?!api|_next|design-system|.*\\..*).*)"]`, so the bare path renders.
- **B:** Move the page under the locale segment
  (`frontend/app/[locale]/design-system/page.tsx`) and drop the old location.

## Notes
Verified 2026-07-23 on branch `email-integration`. Discovered while enumerating
supported UI routes.

## Follow-on fix
Applying option A exposed a second issue: the root `app/layout.tsx` is a bare
passthrough — `<html>`/`<body>` live only in `app/[locale]/layout.tsx`. Once
`/design-system` rendered (outside `[locale]`), Next.js reported
"Missing required html tags". Added `app/design-system/layout.tsx` supplying the
`<html>`/`<body>` shell + `globals.css`.

**Verified:** `GET /design-system` → HTTP 200, `<html>`/`<body>` present, gallery
renders, no missing-root-layout error.

## Files changed
- `frontend/middleware.ts` — matcher excludes `design-system`
- `frontend/app/design-system/layout.tsx` — new standalone layout (html/body)
