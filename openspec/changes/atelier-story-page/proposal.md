## Why

The Atelier Marie has no brand-story / About page. Luxury candle buyers convert on **visual storytelling and trust** — "these are beautiful → they're handmade with care → I want one / this is a gift" — not on a product grid alone. The owner needs a calm, on-brand story page that tells that story, and she needs to **edit every word and photo herself, in both English and Bulgarian**, without a developer. So the content must be admin-managed and stored in the database, following the exact mechanics established by `admin-managed-faq`: a two-table bilingual model, a public/admin API split, and a seed carrying the real copy on day one.

## What Changes

- **New story content model** in SQLite (Layer 1): `about_sections` (seeded, fixed slugs used as page anchors + a fixed section `type`) and `about_items` (child rows for the card / timeline / collection sections), following the bilingual pattern from `admin-managed-faq` and `dynamic-categories` (`_en` required, `_bg` nullable with `COALESCE` fallback).
- **Admin-uploaded images.** Section and item image fields store a WebP `image_id` produced by the existing `app/services/image_service.py` pipeline (magic-byte validation, Pillow resize, EXIF strip, path-traversal guard). No new storage subsystem — reuse.
- **Section-level publish toggle + reorder** (the extra power over FAQ): admin can hide/show a whole section and reorder sections. Slugs and `type` stay fixed so deep-link anchors and per-type rendering never break.
- **New public API** `GET /v1/about?locale=` — published sections (with their published items) in order, localized.
- **New admin API** under `/v1/admin/about` — edit section text, CRUD on items, reorder sections and items, publish toggle, image upload/clear; exposes both languages.
- **New public page** at `/[locale]/atelier` — 10 sections rendered by type (hero, text+image, centered text band, card grid, making-process timeline, full-width atelier image, collections grid, emotional close, custom-order CTA). Emits `AboutPage`/`Organization` JSON-LD for SEO.
- **New admin management UI** at `/[locale]/admin/atelier` — sections listed in order, edit form with **EN + BG side by side**, image upload per section/item, item CRUD, reorder, publish toggle.
- **Seed initial content** — the owner's exact English copy plus a **drafted full Bulgarian translation** (in `seed-content.md`), so the page is populated on launch and the Bulgarian can be reviewed in the seed / admin UI before go-live.
- **Discoverability** — a link to `/atelier` in the main navigation and the footer.

## Capabilities

### New Capabilities
- `about-management`: The `about_sections` + `about_items` tables, bilingual storage + locale-fallback resolution, text sanitization, image handling via `image_service`, and the seed of initial content (EN + drafted BG).
- `about-public-api`: `GET /v1/about` returning published, localized, ordered sections with their items.
- `about-admin-api`: Admin section-text editing, item CRUD, section/item reorder, publish toggle, and image upload/clear under `/v1/admin/about`.
- `about-page`: The public `/[locale]/atelier` page — one renderer per section `type`, section anchors, responsive stacking, JSON-LD.
- `about-admin-ui`: The `/[locale]/admin/atelier` management interface for editing bilingual content and uploading images.

### Modified Capabilities
- `global-layout`: Add an "Atelier" (story) link to the main navigation and the footer.

## Impact

- **Backend:** new `app/models/about.py`, `app/services/about_service.py`, `app/routes/about.py`; schema additions in `app/database.py` (two tables + seed); text passes through `app/utils/sanitize.py`; images reuse `app/services/image_service.py`. All Layer 1, SQLite only, responses <200ms.
- **Frontend:** new `app/[locale]/atelier/page.tsx`, `components/atelier/` (one component per section type + `AtelierAdminForm`), `app/[locale]/admin/atelier/`; edits to `components/layout/Header.tsx` + `Footer.tsx`, `lib/types.ts`, `lib/api-client.ts` / `lib/mock-api.ts`, and `lib/seo.ts`.
- **No Layer 2 involvement.** The store works identically whether or not this page exists.
