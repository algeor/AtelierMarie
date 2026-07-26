## Context

The store needs a luxury brand-story page, and the owner needs to edit it herself in English and Bulgarian, including the photos. The store is already bilingual (`next-intl`, locales `["en","bg"]`, `localePrefix: "always"`, routes under `app/[locale]/`) and has a proven pattern for admin-managed bilingual content: `admin-managed-faq` (two tables — a seeded parent with stable slugs + editable child rows, `_en` required / `_bg` nullable resolved by `COALESCE`, public/admin API split, seed with drafted BG) which itself follows `dynamic-categories`. It also already has a hardened image pipeline: `app/services/image_service.py` (magic-byte validation, Pillow resize to WebP, EXIF strip, path-traversal prevention) used by `product_image_service`.

This design copies the FAQ mechanics and adds exactly two things the story page needs beyond FAQ: **heterogeneous section types** and **admin-uploaded images**, plus **section-level publish toggle + reorder**.

Constraints: Layer 1 only (SQLite, WAL), responses <200ms, no Layer 2 coupling, all user-facing text sanitized via `app/utils/sanitize.py`, thin routes / fat services.

## Goals / Non-Goals

**Goals:**
- Owner edits all story copy, section headings, and photos in both languages, no developer needed.
- One calm, luxury, mobile-friendly page telling the full story (all 10 sections).
- Stable per-section anchors (`/atelier#process`) that survive reorder/toggle.
- Ship populated on day one via a seed carrying the exact EN copy + a full drafted BG translation.
- Reuse `admin-managed-faq` conventions and the existing `image_service` pipeline for consistency.

**Non-Goals:**
- No rich-text editor. Body text is plain text with blank-line paragraphs + simple `* `/`- ` bullet lines (same renderer approach as FAQ).
- No admin-created *section types or slugs*. The 10 sections are seeded with fixed slugs and a fixed `type`; admin edits text/images, toggles visibility, and reorders — but cannot add a new section or change a section's type. (Adding a section is a follow-up change, exactly as FAQ scoped it.)
- Page is **not** longer than the supplied copy — no biography bloat.
- No animations beyond gentle fades/reveals; no parallax.

## Decisions

### 1. Two tables: seeded `about_sections` + editable `about_items`
```sql
CREATE TABLE about_sections (
  slug          TEXT PRIMARY KEY,        -- fixed anchor: hero|story|philosophy|differentiators|
                                         --   process|atelier|values|collections|emotional|custom_cta
  type          TEXT NOT NULL,           -- fixed: hero|text_image|text_band|cards|timeline|
                                         --   collections|cta_band  (drives the renderer)
  heading_en    TEXT NOT NULL,
  heading_bg    TEXT,
  subheading_en TEXT,
  subheading_bg TEXT,
  body_en       TEXT,                    -- plain text, \n paragraphs (nullable: cards/collections
  body_bg       TEXT,                    --   sections may carry only a heading + items)
  cta_label_en  TEXT,                    -- hero / emotional / custom_cta only
  cta_label_bg  TEXT,
  cta_href      TEXT,
  image_id      TEXT,                    -- WebP id from image_service (hero bg, story, atelier)
  sort_order    INTEGER NOT NULL DEFAULT 0,
  is_published  INTEGER NOT NULL DEFAULT 1,
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
);

CREATE TABLE about_items (                -- children of cards / timeline / collections sections
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  section      TEXT NOT NULL REFERENCES about_sections(slug),
  title_en     TEXT NOT NULL,
  title_bg     TEXT,
  text_en      TEXT,
  text_bg      TEXT,
  image_id     TEXT,                      -- timeline step / collection tile photo (cards: none)
  link_href    TEXT,                      -- collection tile → filtered products (nullable)
  sort_order   INTEGER NOT NULL DEFAULT 0,
  is_published INTEGER NOT NULL DEFAULT 1,
  created_at   TEXT NOT NULL,
  updated_at   TEXT NOT NULL
);
CREATE INDEX idx_about_items_section_order ON about_items(section, sort_order);
```
**Why two tables:** identical reasoning to FAQ — sections carry stable anchor slugs + a fixed render `type` that must not drift; repeating child content (4 differentiator cards, 6 process steps, 4 values, 3 collection tiles) lives as ordered rows. **Why fixed slugs + type:** nav/product deep-links target `#process` etc., and the frontend picks a renderer by `type`; letting admins invent either would break links or rendering. Editing text/images and toggling/reordering is safe, so those are allowed.

### 2. Section `type` → renderer map
| type | sections | renders | has items |
|---|---|---|---|
| `hero` | hero | full-bleed image + title/subtitle overlay + CTA button; body as centered welcome band below | no |
| `text_image` | story, atelier | two-column image + heading + body (stacks on mobile) | no |
| `text_band` | philosophy, emotional | centered heading + subheading + body on cream/soft bg; optional CTA | no |
| `cards` | differentiators, values | heading + subheading, then a grid of item cards (title + text, no image) | yes |
| `timeline` | process | heading + intro body, then ordered steps (image + title + one sentence) | yes |
| `collections` | collections | heading + subheading, then image tiles (title + short text, linking to filtered products) | yes |
| `cta_band` | custom_cta | heading + body + button | no |

Only these types exist; the set is closed. Frontend renders `switch(section.type)`; an unknown type is skipped (defensive).

### 3. Bilingual storage = side-by-side columns with COALESCE fallback
Mirrors FAQ / `dynamic-categories` exactly. Public resolution: `en` → `*_en`; `bg` → `COALESCE(*_bg, *_en)`. Admin API returns raw `*_en` + `*_bg` for the side-by-side edit form.

### 4. Images reuse `image_service` — admin upload, no new storage
Section and item `image_id` are produced by the **existing** `app/services/image_service.py` (`validate_image_file` + `process_image` → WebP, EXIF-stripped, size/pixel-capped). The admin API gets `POST .../image` (multipart) and `DELETE .../image` per section/item, following the product-image upload endpoint already in `app/routes/admin.py`. Public API returns the resolved image URL/path (same convention product images use). No DuckDB, no external storage — WebP files on disk exactly like product images.

### 5. Public vs admin API split
- **Public** `GET /v1/about?locale=` → `{ sections: [{ slug, type, heading, subheading, body, cta: {label, href}?, image, items: [{ id, title, text, image, link }] }] }`. Published sections only, published items only, ordered by `sort_order`, single localized string per field. No auth.
- **Admin** under `/v1/admin/about` (behind `require_admin`): `GET` returns raw bilingual rows + `is_published` + `image_id`; `PATCH /sections/{slug}` (text/cta); item `POST`/`PATCH`/`DELETE`; `POST /sections/reorder` and `POST /sections/{slug}/items/reorder`; `PATCH .../publish`; image `POST`/`DELETE`. Mirrors the FAQ admin API + the product-image endpoints.

### 6. Body format: sanitized plain text, rendered as paragraphs + bullets
Identical to FAQ Decision 4. Stored as plain text with `\n`; blank-line blocks → paragraphs; consecutive `* `/`- ` lines → `<ul>`. All text sanitized via `app/utils/sanitize.py` on write. No HTML-injection surface, no rich-text editor.

### 7. Frontend: server page + typed section components
- `app/[locale]/atelier/page.tsx` — server component: fetches `/v1/about`, maps sections to components by `type`, emits JSON-LD via `lib/seo.ts`, sets metadata. Each section wrapper gets `id={slug}` + `scroll-margin-top`.
- `components/atelier/` — one component per type (`Hero`, `TextImage`, `TextBand`, `CardGrid`, `ProcessTimeline`, `CollectionsGrid`, `CtaBand`). Client interactivity only where needed (e.g. reveal-on-scroll); most are server-rendered.
- Styling from existing tokens: `warm-ivory`/`cream` backgrounds, white cards with subtle shadow + `rounded-2xl`, `charcoal`/`soft-brown` text, `muted-gold` decorative accents, `font-heading` (Playfair) for headings. Generous section spacing (desktop ~120px, mobile ~72px). Mobile stacks image → title → text → button.

### 8. Route & navigation
- Route: `/[locale]/atelier` (on-brand with "Inside Our Atelier"; `/story` considered and rejected as less distinctive).
- Linked in the **main navigation** and the **footer** (`components/layout/Header.tsx`, `Footer.tsx`).

### 9. Seed
`app/database.py` seeds all 10 sections (+ their items) with the exact EN copy and drafted BG **only if `about_sections` is empty** (idempotent, matches `product_seed` / FAQ). Full bilingual copy lives in `seed-content.md`. All sections seed `is_published=1` (owner wants the full page live). Editing/deleting seeded rows afterward is never overwritten. Seed image fields are `NULL` → sections render with a tasteful placeholder until the owner uploads photos.

## Risks / Trade-offs

- **Bulgarian copy is a draft** → owner reviews it in `seed-content.md` / admin UI before launch; all `*_bg` are nullable so anything cleared still renders EN rather than blank.
- **No seeded images** → page launches with placeholders; owner uploads real photos via admin. Acceptable — text is the seed's job; photos are inherently owner-specific.
- **Collections tiles link to filtered products** (`/products?category=floral|sculptural|bespoke`) → those category slugs must exist (ties to `dynamic-categories`). Seeded `link_href` values are **drafts**; if a category doesn't exist yet the tile can link to `/products` or be hidden. Flagged for owner/dev confirmation.
- **Custom-order CTA target** → there is no bespoke-order flow yet; `custom_cta.cta_href` seeds to `/contact` as a placeholder, to be pointed at a real custom-order path when one exists.
- **Reorder + fixed anchors** → anchors are keyed on `slug`, not position, so reordering never breaks deep-links; a *hidden* section's anchor simply resolves to nothing (acceptable).
- **DB fetch vs static i18n** → single indexed query + small item fan-in, well under 200ms; cacheable. Acceptable for the editability requirement.
- **Plain-text renderer is limited** → matches all current copy (prose + one implicit list); richer formatting is a future change, not a bolt-on.

## Migration Plan

- Additive schema only (two new tables) — no changes to existing tables, no data rewrite. Plain `CREATE TABLE IF NOT EXISTS` + idempotent seed on startup; follows the `products_new` rebuild convention only if a column is later added.
- Deploy backend (tables + seed populate on startup) → deploy frontend → owner uploads photos and reviews BG. Rollback = remove the route + nav/footer links; the tables are inert and harmless if left in place.
