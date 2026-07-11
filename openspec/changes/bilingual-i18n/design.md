## Context

Atelier Marie is a Next.js 14 (App Router) + FastAPI e-commerce platform. Currently English-only with hardcoded strings throughout the frontend and single-language product content in SQLite. The primary customer base is Bulgarian, with a secondary international audience.

The frontend uses Playfair Display + Inter fonts (both support Cyrillic). The backend follows a thin-routes/fat-services pattern with SQLite (WAL mode). Products are identified by text slugs (e.g., `lavender-dream-300ml`). Sessions are cookie-based with eager DB row creation.

## Goals / Non-Goals

**Goals:**
- Serve the site in Bulgarian (BG) or English (EN) based on browser language, with manual override
- SEO indexing in both languages via subdirectory routing (`/bg/...`, `/en/...`)
- Bilingual product content managed through the admin panel
- Translation staleness tracking so the owner knows when content is out of sync
- Graceful fallback (never hide content due to missing translations)
- Store locale preference for future email localization

**Non-Goals:**
- Third language support (strictly BG + EN — no extensible locale framework needed)
- Machine translation or auto-translate features
- Backend API localization (API responses stay English; frontend handles display mapping)
- Per-user locale in auth/profile (locale is session-level, not account-level)
- Translating user-generated content (comments stay in whatever language the user wrote them)

## Decisions

### 1. Locale detection: `Accept-Language` header (not IP geolocation)

**Choice:** Next.js middleware reads `Accept-Language` from the request. If it contains `bg`, redirect to `/bg/`. Otherwise, redirect to `/en/`.

**Why not IP geolocation:** Adds third-party dependency (MaxMind or API), doesn't reflect language preference (a tourist in Bulgaria still wants English), and costs latency. Browser language correctly answers "what language does this person prefer?" which is what we actually care about.

**Alternatives considered:**
- IP geolocation (MaxMind GeoLite2) — too complex for two-language case
- navigator.language client-side — causes flash of wrong language on first load

### 2. URL strategy: Subdirectory routing (`/bg/...`, `/en/...`)

**Choice:** All routes live under a `[locale]` dynamic segment. Middleware redirects bare `/` to the appropriate locale prefix.

**Why not cookie-only (same URLs):** Kills SEO in Bulgarian. Google needs distinct URLs to index both language versions. Subdirectory approach also makes links shareable with language preserved.

**Structure:**
```
frontend/app/
├── [locale]/           ← 'bg' | 'en'
│   ├── layout.tsx      ← sets <html lang={locale}>, provides locale context
│   ├── page.tsx
│   ├── products/
│   ├── checkout/
│   ├── orders/
│   ├── admin/
│   └── account/
├── middleware.ts       ← locale detection + redirect
```

### 3. Translation system: `next-intl` with JSON message files

**Choice:** Use `next-intl` library with static JSON files (`messages/en.json`, `messages/bg.json`) for UI strings.

**Why `next-intl`:** Purpose-built for Next.js App Router, supports server components, handles pluralization, integrates with middleware routing. Lightweight, well-maintained, no build step required.

**Why not custom solution:** Reinventing ICU message formatting, pluralization, and server/client hydration is not worth it for a two-language shop.

**Alternatives considered:**
- `react-intl` — heavier, less App Router integration
- Custom `t()` with plain JSON lookup — loses pluralization, interpolation, type safety
- `i18next` / `next-i18next` — more suited to Pages Router

### 4. Product content storage: Suffix columns (`name_en`, `name_bg`)

**Choice:** Add `_en` and `_bg` suffixed columns directly to the products table. No separate translations table.

**Why:** Only two languages, ever. A JOIN-based translations table adds complexity (extra table, extra queries, potential N+1) for zero benefit when the language set is fixed and small.

**Schema change:**
```sql
ALTER TABLE products ADD COLUMN name_bg TEXT;
ALTER TABLE products ADD COLUMN description_bg TEXT;
ALTER TABLE products ADD COLUMN translation_stale_bg INTEGER DEFAULT 0;
ALTER TABLE products ADD COLUMN translation_stale_en INTEGER DEFAULT 0;
-- Existing name/description renamed to name_en/description_en
```

**Alternatives considered:**
- Separate `product_translations` table (product_id, locale, name, description) — correct for N languages, overkill for 2
- JSON column with both translations — loses queryability, harder to migrate

### 5. API locale handling: Query parameter with header fallback

**Choice:** Product API accepts `?locale=bg|en`. If not provided, falls back to `Accept-Language` header, then defaults to `en`. API always returns the requested locale's content with fallback to the other language if empty.

**Why not path-based API locale:** Backend is language-agnostic (error codes are English). Only product content is locale-dependent. A query param keeps it surgical.

### 6. Locale persistence: Cookie + session DB field

**Choice:** When user clicks the toggle or middleware detects locale:
1. Set `NEXT_LOCALE` cookie (read by middleware on next request)
2. Send preference to backend → stored in `sessions.preferred_locale`

**Why both:** Cookie handles the frontend redirect (stateless, fast). DB field enables server-side use (email templates, order records).

### 7. Translation staleness: Simple boolean flags

**Choice:** `translation_stale_bg` and `translation_stale_en` boolean columns on products. When `name_en` or `description_en` is updated, set `translation_stale_bg = 1` (and vice versa). Admin clears by updating the stale side.

**Why not timestamps/diff:** Over-engineering for a single-person workflow. A boolean "needs attention" flag is sufficient when the owner manages both languages.

### 8. FTS5 search: Dual index

**Choice:** Maintain two FTS5 virtual tables (`products_fts_en`, `products_fts_bg`) synced via triggers on the respective `_en`/`_bg` columns. Product search queries the FTS table matching the current locale.

**Why:** FTS5 doesn't handle multilingual content well in a single index (different tokenization rules, stopwords). Separate indexes keep search quality high for both languages.

## Risks / Trade-offs

**[Large frontend restructure]** → Moving all pages under `[locale]/` is a big diff touching every route. Mitigation: Do this as a single atomic refactor step before adding translations — keeps the migration reviewable.

**[Double content maintenance]** → Owner must write every product description twice. Mitigation: Staleness flags surface what needs attention. Fallback ensures the site never looks broken even if BG lags.

**[FTS5 dual index complexity]** → Two indexes means two sets of triggers, slightly more schema surface. Mitigation: Triggers are mechanical (generated from template), and the alternative (single index with mixed-language content) produces worse search results.

**[SEO cold start]** → New `/bg/` URLs have no search history. Mitigation: Proper `hreflang` tags, sitemap with both locales, and 301 redirects from old single-language URLs to `/en/` equivalents preserve existing ranking.

**[Cookie/middleware race]** → First request before cookie is set sees a redirect. Mitigation: Middleware redirect is 307 (temporary), fast, and only happens once per new visitor.

## Migration Plan

1. **Database migration:** Rename `name` → `name_en`, `description` → `description_en`. Add `name_bg`, `description_bg`, staleness booleans, `preferred_locale` on sessions. Existing data becomes the EN version; BG fields start NULL (fallback covers this).

2. **Frontend restructure:** Move all routes under `[locale]/`. Add middleware. Verify all existing pages work at `/en/...` paths. This is a no-behavior-change refactor.

3. **Translation system:** Add `next-intl`, create `messages/en.json` with all extracted strings, wire up `useTranslations()` in components. Site still works in English only at this point.

4. **Bulgarian translations:** Create `messages/bg.json`. Site now renders in both languages.

5. **Product content:** Update API + admin to handle dual fields. Admin form shows both-language inputs. Product pages render locale-appropriate content.

6. **SEO:** Add `hreflang` tags, generate dual-locale sitemap, add 301 redirects from old URLs.

7. **Rollback:** If issues arise, middleware can be configured to hard-redirect everything to `/en/` and the site works exactly as before (EN-only).

## Open Questions

- Should product slugs/IDs remain language-neutral (e.g., `lavender-dream-300ml` in both `/bg/` and `/en/` URLs)? Or should BG have transliterated slugs? (Recommendation: keep neutral — simpler, slug is an ID not display text)
