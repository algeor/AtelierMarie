## Why

Customers repeatedly ask the same questions about handmade candles, care/safety, custom orders, and shipping — and there is nowhere on the site to reassure them before purchase. A calm, on-brand FAQ page answers those questions and reinforces craftsmanship and personal service. The owner also needs to edit this content herself, in **both English and Bulgarian**, without a developer — so the content must be admin-managed and stored in the database, not hardcoded.

## What Changes

- **New FAQ content model** in SQLite (Layer 1): `faq_sections` (seeded, stable slugs used as page anchors) and `faq_items` (bilingual question/answer pairs), following the bilingual pattern established by `dynamic-categories` (`_en` required, `_bg` nullable with `COALESCE` fallback).
- **New public API** `GET /v1/faq` — published items grouped by section, localized via `?locale=`.
- **New admin API** under `/v1/admin/faq` — full CRUD on items, reorder within a section, publish/hide toggle, edit section titles; exposes both languages.
- **New public FAQ page** at `/[locale]/faq` — single centred column, four accordion sections (one-open-at-a-time **per section**, 250–350ms animation), muted-gold decorative section lines, contact banner, and three trust cards. Includes `FAQPage` JSON-LD structured data for SEO.
- **New admin management UI** at `/[locale]/admin/faq` — items grouped by section, edit form with **EN + BG side by side**, reorder, publish toggle, create/delete.
- **Seed initial content** — the owner's exact English copy plus a drafted Bulgarian translation, so the page is populated on launch and the Bulgarian can be reviewed in the seed.
- **Discoverability without main-nav clutter** — footer link, product-page contextual links (Care / Custom / Shipping), and a small "Questions?" link near the Add to Cart button that jumps to the relevant section.
- Page chrome (hero title/subtitle, contact banner text, trust cards) stays in `messages/*.json` — only Q&A items and section titles are DB-managed.

## Capabilities

### New Capabilities
- `faq-management`: The `faq_sections` and `faq_items` tables, bilingual storage + locale-fallback resolution, answer sanitization, and the seed of initial content.
- `faq-public-api`: `GET /v1/faq` returning published, localized, section-grouped content.
- `faq-admin-api`: Admin CRUD, reorder, publish toggle, and section-title editing under `/v1/admin/faq`.
- `faq-page`: The public `/[locale]/faq` page — hero, accordion behavior, section anchors, contact banner, trust cards, and JSON-LD.
- `faq-admin-ui`: The `/[locale]/admin/faq` management interface for editing bilingual content.

### Modified Capabilities
- `product-detail`: Add a small "Questions?" link near Add to Cart and contextual links (Candle Care / Custom Orders / Shipping & Returns) that deep-link to the matching FAQ section anchor.
- `global-layout`: Add an FAQ link to the footer (FAQ is intentionally kept out of the main navigation).

## Impact

- **Backend:** new `app/models/faq.py`, `app/services/faq_service.py`, `app/routes/faq.py`; schema additions in `app/database.py` (two tables + `updated_at` triggers + marker-guarded seed migration). FAQ content is trusted admin input, stored raw (no write-time HTML escaping) and made XSS-safe at render. All Layer 1, SQLite only, responses <200ms.
- **Frontend:** new `app/[locale]/faq/page.tsx`, `components/faq/FaqAccordion.tsx`, `app/[locale]/admin/faq/`; edits to `components/layout/Footer.tsx`, the product detail page, `lib/types.ts`, `lib/api-client.ts` / `lib/mock-api.ts`, and `lib/seo.ts`; new chrome strings in `messages/en.json` + `messages/bg.json`.
- **No Layer 2 involvement.** Store works identically whether or not the FAQ feature is enabled.
