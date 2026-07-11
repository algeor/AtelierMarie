## Why

Atelier Marie is a Bulgarian family business selling primarily to Bulgarian customers, with a secondary international audience. The site is currently English-only, which creates friction for the primary audience and misses Bulgarian search engine visibility entirely. Adding bilingual support (BG + EN) makes the shop feel native to Bulgarian speakers while keeping it accessible internationally — and doubles SEO surface area.

## What Changes

- All user-facing content renders in the user's detected/chosen language (BG or EN)
- Frontend restructured with subdirectory routing (`/bg/...`, `/en/...`) for SEO
- Next.js middleware detects browser `Accept-Language` and redirects to appropriate locale
- Language toggle (flag button) in header for manual switching; preference persisted in cookie
- Product content stored in both languages in the database (dual fields: `name_en`/`name_bg`, `description_en`/`description_bg`)
- Admin UI supports entering and managing content in both languages with staleness indicators
- Translation fallback: if one language is missing, show the other (never hide products)
- Preferred locale stored with sessions/orders for future email localization
- Backend API stays English-only (logs, error codes); frontend maps codes to localized display strings
- `hreflang` tags and dual-language sitemap for proper SEO indexing
- Fonts updated to include Cyrillic subset (same fonts: Playfair Display + Inter)

## Capabilities

### New Capabilities

- `locale-detection`: Browser language detection via `Accept-Language` header, cookie persistence, and middleware redirect logic
- `locale-routing`: Subdirectory-based locale routing (`/bg/...`, `/en/...`), Next.js `[locale]` dynamic segment, SEO tags (`hreflang`, sitemap)
- `locale-ui-strings`: Static UI string translation system (JSON translation files, frontend translation helper, error code mapping)
- `locale-product-content`: Bilingual product content in database (dual fields, fallback logic, API locale-aware responses)
- `locale-admin`: Admin UI for managing bilingual content (dual input fields, staleness indicators, admin UI translation)
- `locale-toggle`: Language toggle component (flag button in header, cookie update, locale switch navigation)

### Modified Capabilities

- `product-public-api`: Product endpoints return locale-aware content (accept locale parameter, fallback to other language)
- `product-admin-api`: Admin product endpoints accept and return dual-language fields, track translation staleness
- `global-layout`: Header gains language toggle; `<html lang>` set dynamically; font subset includes Cyrillic
- `session-lifecycle`: Sessions store `preferred_locale` for downstream use (emails, order records)

## Impact

- **Frontend**: Major restructure — all pages move under `[locale]/` segment; every component with user-facing text needs translation keys
- **Database**: Schema migration adding `_en`/`_bg` columns to products, `preferred_locale` to sessions, staleness booleans
- **Backend API**: Product service gains locale-awareness; admin endpoints expand to handle dual-language input
- **Dependencies**: Likely `next-intl` or similar i18n library for Next.js; no new backend dependencies
- **Existing data**: Migration converts current `name`/`description` to `name_en`/`description_en`; `_bg` fields start empty (fallback covers this)
- **Tests**: Route tests need locale prefix; new tests for detection, fallback, and staleness logic
