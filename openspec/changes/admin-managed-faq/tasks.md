## 1. Database schema & seed

- [x] 1.1 Add `faq_sections` table (slug PK, title_en NOT NULL, title_bg, icon, sort_order, created_at/updated_at `DEFAULT (datetime('now'))`) to `app/database.py` schema init
- [x] 1.2 Add `faq_items` table (id PK AUTOINCREMENT, section FK→faq_sections.slug, question_en NOT NULL, question_bg, answer_en NOT NULL, answer_bg, sort_order, is_published DEFAULT 1, created_at/updated_at) + index on (section, sort_order)
- [x] 1.3 Add `AFTER UPDATE` triggers `faq_sections_updated_at` and `faq_items_updated_at` (mirror `products_updated_at`)
- [x] 1.4 Add marker-guarded one-time seed migration (schema_migrations marker, like `dynamic-categories`) inserting the 4 sections + all items from the seed content in `faq-management` spec (exact EN + BG draft), `is_published = 1`
- [x] 1.5 Verify seed runs once on a fresh DB and re-run is a no-op (does not re-create edited/deleted rows)

## 2. Backend models

- [x] 2.1 `app/models/faq.py`: public `FaqItemResponse` (id, question, answer), `FaqSectionResponse` (slug, title, icon, items), `FaqResponse`
- [x] 2.2 Admin models: `FaqItemAdminResponse` (both languages + is_published + sort_order + timestamps), `FaqSectionAdminResponse`
- [x] 2.3 Request models: `CreateFaqItemRequest` (section, question_en, answer_en required; question_bg, answer_bg, sort_order optional), `UpdateFaqItemRequest` (all optional incl. is_published), `ReorderFaqItemsRequest`, `UpdateFaqSectionRequest` (title_en?, title_bg?, icon?, sort_order? — no slug)

## 3. Backend service

- [x] 3.1 `app/services/faq_service.py`: `get_public_faq(locale)` — published items grouped by section, ordered, localized via COALESCE fallback; unknown locale → en; omit empty sections
- [x] 3.2 `list_faq_admin()` — all sections + items (incl. unpublished), both languages
- [x] 3.3 `create_item()` / `update_item()` / `delete_item()` — validate section slug exists; store question/answer as **raw text** (do NOT `html.escape` — trusted admin content; escaping double-encodes punctuation React renders literally); `updated_at` handled by DB trigger
- [x] 3.4 `set_published(item_id, published)` toggle
- [x] 3.5 `reorder_items(section, ordered_ids)` — update sort_order scoped to section
- [x] 3.6 `update_section(slug, ...)` — edit title_en/title_bg/icon/sort_order; reject/ignore slug change
- [x] 3.7 Custom exceptions (`FaqItemNotFoundError`, `FaqSectionNotFoundError`) + chaining

## 4. Backend routes

- [x] 4.1 `app/routes/faq.py`: public `GET /v1/faq?locale=` (no auth, response_model=FaqResponse)
- [x] 4.2 Admin router under `/v1/admin/faq` guarded by `require_admin`: `GET` list, `POST` item, `PATCH`/`DELETE` item by id
- [x] 4.3 Admin `PATCH /v1/admin/faq/reorder` (or per-section) and `PATCH /v1/admin/faq/sections/{slug}`
- [x] 4.4 Map service exceptions to HTTP (404/422); register router in `app/main.py`

## 5. Backend tests

- [x] 5.1 Service tests: locale fallback (bg→en per field), published-only filtering, empty-section omission, unknown-locale default
- [x] 5.2 Service tests: create/update/delete, raw storage preserves apostrophes/`&`/em-dashes and newlines (no double-escaping), publish toggle, reorder within section, section title edit + slug immutability
- [x] 5.3 Route tests: public GET shape/localization; admin CRUD; admin auth required (401/403 for non-admin)
- [x] 5.4 Seed idempotency test (fresh DB populates; re-init does not clobber)

## 6. Frontend — types, API client, i18n chrome

- [x] 6.1 Add FAQ interfaces to `lib/types.ts` (mirror public + admin response shapes)
- [x] 6.2 Add FAQ methods to `lib/api-client.ts` and matching mocks in `lib/mock-api.ts` (public get + admin CRUD/reorder/section)
- [x] 6.3 Add `faq` chrome strings (hero title/subtitle, Contact Us, banner, trust cards, footer link label) to `messages/en.json` + `messages/bg.json`

## 7. Frontend — public FAQ page

- [x] 7.1 `components/faq/FaqAccordion.tsx` (client): per-section single-open state, 250–350ms animation, ≥48px tap targets, `rounded-2xl`, tokens (warm-ivory/white/charcoal/soft-brown/muted-gold)
- [x] 7.2 Answer renderer: blank-line paragraphs + `* `/`- ` bullet lines → `<ul>`
- [x] 7.3 `app/[locale]/faq/page.tsx` (server): fetch `/v1/faq`, hero + Contact Us link, sections with icon + decorative accent line + `id=slug` + scroll-margin, contact banner, 3 trust cards; single centred column max-w ~900px, responsive padding
- [x] 7.4 `FAQPage` JSON-LD via `lib/seo.ts` + localized metadata
- [x] 7.5 Verify anchors (`#candles`/`#care`/`#custom`/`#shipping`) scroll cleanly below header

## 8. Frontend — discoverability

- [x] 8.1 Add localized FAQ link to `components/layout/Footer.tsx` (not in header nav)
- [x] 8.2 Product detail: contextual links (Candle Care → #care, Custom Orders → #custom, Shipping & Returns → #shipping)
- [x] 8.3 Product detail: small "Questions?" link near Add to Cart → relevant FAQ anchor

## 9. Frontend — admin management UI

- [x] 9.1 `app/[locale]/admin/faq/` page under admin guard: items grouped by section with published/hidden indicator
- [x] 9.2 Item editor: EN + BG fields side by side (question + answer), EN required client-side validation, save via admin API
- [x] 9.3 Create / delete item, publish-hide toggle, reorder within section (no full reload)
- [x] 9.4 Add FAQ entry to admin navigation/sidebar

## 10. Frontend tests

- [x] 10.1 `FaqAccordion` tests: one-open-per-section, sections independent, bullet rendering
- [x] 10.2 Admin FAQ form test: EN-required validation, both-language save calls API

## 11. Verification

- [x] 11.1 `make lint` and `make test` pass (backend + frontend)
- [ ] 11.2 Manual: `/en/faq` and `/bg/faq` render seeded content; edit an item in admin and confirm it updates publicly; deep-link from a product page lands on the right section
