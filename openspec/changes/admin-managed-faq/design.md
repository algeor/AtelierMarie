## Context

Customers need a reassuring, on-brand FAQ page, and the owner needs to edit that content herself in English and Bulgarian. The store is bilingual already (`next-intl`, locales `["en","bg"]`, `localePrefix: "always"`, routes under `app/[locale]/`). An in-flight change, `dynamic-categories`, has already established the house pattern for admin-managed bilingual content: side-by-side `_en`/`_bg` columns, `_en` required, `_bg` nullable resolved with `COALESCE(*_bg, *_en)`, a public/admin API split, `sort_order`, an active flag, timestamps, and a seed. This design follows that pattern so FAQ content behaves like the rest of the app.

Constraints: Layer 1 only (SQLite, WAL), responses <200ms, no Layer 2 coupling, thin routes / fat services. Note the project sanitizes *anonymous* user input (comments, display names) via `app/utils/sanitize.py`; FAQ content is trusted admin input and is handled differently (see Decision 4).

## Goals / Non-Goals

**Goals:**
- Owner edits all Q&A content and section titles in both languages, no developer needed.
- Public FAQ page is calm, minimal, on-brand, and browsable on mobile.
- Stable per-section anchors so product pages can deep-link (`/faq#care`).
- Ship populated on day one via a seed carrying the exact EN copy + drafted BG.
- Reuse the `dynamic-categories` bilingual conventions for consistency.

**Non-Goals:**
- No rich-text editor. Answers are plain text with newlines + simple `* `/`- ` bullet lines.
- Page chrome (hero, banner text, trust cards) is NOT admin-managed — it stays in `messages/*.json`.
- No admin-created *sections* in v1 (the four sections are seeded with fixed slugs; only their titles are editable). Adding/removing sections is out of scope.
- Deep-links scroll to a section only — they do NOT auto-open a specific question.
- No search/filter within the FAQ.

## Decisions

### 1. Two tables: seeded `faq_sections` + editable `faq_items`
```sql
CREATE TABLE IF NOT EXISTS faq_sections (
  slug        TEXT PRIMARY KEY,          -- candles | care | custom | shipping (stable anchor)
  title_en    TEXT NOT NULL,
  title_bg    TEXT,                      -- nullable → COALESCE fallback
  icon        TEXT,                      -- emoji: 🕯 ✨ 🎁 📦
  sort_order  INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS faq_items (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  section      TEXT NOT NULL REFERENCES faq_sections(slug),
  question_en  TEXT NOT NULL,
  question_bg  TEXT,
  answer_en    TEXT NOT NULL,
  answer_bg    TEXT,
  sort_order   INTEGER NOT NULL DEFAULT 0,
  is_published INTEGER NOT NULL DEFAULT 1,
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_faq_items_section_order ON faq_items(section, sort_order);
```

Timestamps use the repo convention: `TEXT NOT NULL DEFAULT (datetime('now'))`, and `updated_at` is maintained by `AFTER UPDATE` triggers (`faq_sections_updated_at`, `faq_items_updated_at`) mirroring the existing `products_updated_at` / `orders_updated_at` triggers — not by service code.
**Why two tables:** sections carry stable anchor slugs + icons + bilingual titles that must not drift when items change. **Why fixed section slugs:** product pages deep-link to `#care` etc.; letting admins mint slugs would break those links. Editing titles is safe, so titles are editable and slugs are not. **Alternative rejected:** a single flat table with a free-text section string — loses the stable-anchor guarantee and duplicates section titles across rows.

### 2. Bilingual storage = side-by-side columns with COALESCE fallback
Mirrors `dynamic-categories` exactly. Public resolution: `en` → `*_en`; `bg` → `COALESCE(*_bg, *_en)`. **Alternative rejected:** a separate translations table — overkill for exactly two locales and makes the admin "edit both languages in one form" UX harder.

### 3. Public vs admin API split
- **Public** `GET /v1/faq?locale=` → `{ sections: [{ slug, title, icon, items: [{ id, question, answer }] }] }`. Published items only, ordered by `sort_order`, single localized string per field. No auth.
- **Admin** under `/v1/admin/faq` (behind `require_admin`): list returns raw bilingual rows + `is_published`; `POST`/`PATCH`/`DELETE` items; a reorder endpoint; `PATCH` section titles. Mirrors the `product-admin-api` / `category-management` split.

### 4. Answer format: raw plain text, escaped at render
Stored as **raw** plain text with `\n` preserved. Renderer: blank-line-separated blocks become paragraphs; consecutive lines starting with `* ` or `- ` become a `<ul>`. FAQ content is **admin-authored and trusted** (behind `require_admin`), unlike anonymous comments — so it is **not** run through `sanitize_text` on write. That matters: `sanitize_text` is `html.escape` (it *escapes*, it does not strip), and escaping trusted content would double-encode the apostrophes, `&`, and em-dashes that fill this copy, which React then renders literally as `&#x27;` / `&amp;` (the storefront renders body text as a JSX text node, e.g. `CommentCard.tsx` `{comment.body}`). XSS safety comes from React's automatic escaping at render; the JSON-LD block is emitted via safe serialization (`JSON.stringify`, with `<` escaped to prevent `</script>` breakout). This covers the one bulleted answer ("Candle Safety") without a rich-text editor.

### 5. Frontend: server page + client accordion
- `app/[locale]/faq/page.tsx` — server component: fetches `/v1/faq`, renders hero/sections/banner/trust cards, emits `FAQPage` JSON-LD via `lib/seo.ts`, sets metadata. Each section wrapper gets `id={slug}` for anchors + `scroll-margin-top`.
- `components/faq/FaqAccordion.tsx` — client component per section, holds `openId` state → **one open per section** (opening in *Shipping* never collapses *About*). Animate max-height/opacity 300ms via `duration-normal`. Radius `rounded-2xl` (16px). Tap targets ≥48px.
- Styling from existing tokens: `warm-ivory` bg, white/`cream` cards, `charcoal` text, `soft-brown` secondary, `muted-gold` decorative section lines, `font-heading` (Playfair) section titles. Single centred column, `max-w-[900px]`.

### 6. Discoverability (kept out of main nav)
- Footer link in `components/layout/Footer.tsx` → `/[locale]/faq`.
- Product detail: contextual links (Candle Care → `/faq#care`, Custom Orders → `/faq#custom`, Shipping & Returns → `/faq#shipping`) and a small "Questions?" link near Add to Cart → `/faq#care`.

### 7. Seed
Initial content is inserted by a **marker-guarded one-time migration in `app/database.py`**, following the same pattern `dynamic-categories` uses (a `schema_migrations` marker so it runs exactly once and re-runs are a no-op). It seeds the four sections + all items with exact EN copy and drafted BG. Because it is marker-guarded (not "reseed when empty"), later edits or deletions of seeded rows are never re-created on subsequent startups. **Alternative rejected:** a manual `scripts/seed_faq.py` like `seed_products.py` — FAQ is owner-facing content that should populate automatically on deploy without a manual step.

## Risks / Trade-offs

- **Bulgarian copy is a draft** → owner reviews it in the seed / admin UI before launch; `title_bg`/`*_bg` are nullable so anything unreviewed still renders EN rather than blank.
- **DB fetch adds latency vs static i18n** → single indexed query, well under 200ms; response is cacheable and small. Acceptable for the editability requirement.
- **Fixed section set** → if the owner later wants a new section, that's a follow-up change (add a seeded slug); documented as a Non-Goal to avoid anchor breakage now.
- **Plain-text renderer is limited** (paragraphs + bullets only) → matches all current content; richer formatting would be a future change, not a rich-text editor bolt-on.
- **Emoji icons stored as text** → render inconsistently across platforms; acceptable for a small decorative accent, and the field is editable.

## Migration Plan

- Additive schema only (two new tables + their triggers) — no changes to existing tables, no data rewrite. Initial creation is `CREATE TABLE IF NOT EXISTS`; the content seed is a marker-guarded one-time migration (runs once, re-run is a no-op).
- Deploy backend (tables created + seed migration runs on startup) → deploy frontend. Rollback = remove the FAQ routes/link; the tables are inert and harmless if left in place.
