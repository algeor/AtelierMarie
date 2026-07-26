## 1. Backend — schema & model

- [ ] 1.1 Add `about_sections` and `about_items` `CREATE TABLE IF NOT EXISTS` + `idx_about_items_section_order` to `app/database.py` schema setup
- [ ] 1.2 Create `app/models/about.py` — Pydantic schemas: `AboutSectionPublic`, `AboutItemPublic`, `AboutCtaPublic`, admin bilingual raw models (`AboutSectionAdmin`, `AboutItemAdmin`), and request bodies (patch section, create/patch item, reorder, publish toggle)
- [ ] 1.3 Define the closed section `type` set (`hero|text_image|text_band|cards|timeline|collections|cta_band`) as a `Literal` and the fixed slug list in `app/constants.py`

## 2. Backend — seed

- [ ] 2.1 Implement idempotent seed in `app/database.py`: if `about_sections` is empty, insert all 10 sections (order per `seed-content.md`, all `is_published=1`, `image_id=NULL`) + their items
- [ ] 2.2 Transcribe the exact EN + drafted BG copy from `seed-content.md` into the seed (sections 1–10 and all card/timeline/collection items)
- [ ] 2.3 Verify seed runs once (no overwrite when table already populated)

## 3. Backend — service layer

- [ ] 3.1 Create `app/services/about_service.py` with custom exceptions (`AboutSectionNotFoundError`, `AboutItemNotFoundError`, `AboutReorderError`)
- [ ] 3.2 Implement `get_public_about(locale)` — published sections + published items, ordered, localized via `COALESCE(*_bg, *_en)` for `bg`; resolve `image_id` to URL/path
- [ ] 3.3 Implement admin reads returning raw `*_en`/`*_bg` + `is_published` + `image_id`
- [ ] 3.4 Implement `update_section_text` (heading/subheading/body/cta, sanitize via `app/utils/sanitize.py`; reject slug/type change)
- [ ] 3.5 Implement item create / update / delete (sanitize text; enforce parent section exists)
- [ ] 3.6 Implement `reorder_sections` and `reorder_items` (validate the submitted set matches existing rows; update `sort_order`)
- [ ] 3.7 Implement `set_section_published` / `set_item_published` toggles
- [ ] 3.8 Implement image set/clear on section & item — reuse `image_service.validate_image_file` + `process_image` → WebP `image_id`; DELETE sets `image_id=NULL`

## 4. Backend — routes

- [ ] 4.1 Create `app/routes/about.py` with public router: `GET /v1/about` (`?locale=`, no auth, `response_model`)
- [ ] 4.2 Add admin router under `/v1/admin/about` (all behind `require_admin`): `GET` list, `PATCH /sections/{slug}`, item `POST`/`PATCH`/`DELETE`
- [ ] 4.3 Add `POST /sections/reorder`, `POST /sections/{slug}/items/reorder`, and `PATCH .../publish` endpoints
- [ ] 4.4 Add multipart `POST .../image` and `DELETE .../image` for sections and items (mirror product-image upload in `app/routes/admin.py`)
- [ ] 4.5 Register both routers in `app/main.py`; map service exceptions to HTTP (404/409/422) via existing handlers

## 5. Backend — tests

- [ ] 5.1 Service tests: locale fallback (bg→en), publish filtering, reorder validation, slug/type immutability, sanitization strips HTML
- [ ] 5.2 Route tests (public): `GET /v1/about` shape, ordering, hidden sections/items excluded, `<200ms` sanity
- [ ] 5.3 Route tests (admin): auth required (401/403), section PATCH, item CRUD, reorder, publish toggle
- [ ] 5.4 Image tests: valid upload → `image_id` set; non-image rejected; clear → NULL
- [ ] 5.5 Seed test: 10 sections + expected item counts present after startup; idempotent on second run

## 6. Frontend — types & API client

- [ ] 6.1 Add `AboutSection`, `AboutItem`, `AboutCta` interfaces to `frontend/lib/types.ts` (mirror public API)
- [ ] 6.2 Add `getAbout(locale)` to `frontend/lib/api-client.ts` and matching mock in `frontend/lib/mock-api.ts` (identical shape)
- [ ] 6.3 Add admin about calls (list, patch section, item CRUD, reorder, publish, image upload/clear) to the API client

## 7. Frontend — public page

- [ ] 7.1 Create `frontend/app/[locale]/atelier/page.tsx` (server component): fetch `/v1/about`, set metadata, emit JSON-LD via `lib/seo.ts`
- [ ] 7.2 Create section components in `frontend/components/atelier/`: `Hero`, `TextImage`, `TextBand`, `CardGrid`, `ProcessTimeline`, `CollectionsGrid`, `CtaBand`
- [ ] 7.3 Implement `switch(section.type)` renderer dispatch; skip unknown types; wrap each section with `id={slug}` + `scroll-margin-top`
- [ ] 7.4 Implement body renderer: blank-line blocks → paragraphs, consecutive `* `/`- ` lines → `<ul>`
- [ ] 7.5 Apply design tokens (warm-ivory/cream, rounded-2xl cards, muted-gold accents, Playfair headings), generous section spacing, mobile stacking, image placeholders

## 8. Frontend — admin UI

- [ ] 8.1 Create `frontend/app/[locale]/admin/atelier/` page behind the existing admin guard; list sections in order with type + publish state
- [ ] 8.2 Section edit form with EN + BG fields side by side (heading/subheading/body/cta), saved in one request
- [ ] 8.3 Item management UI (create/edit/delete) for cards/timeline/collections sections
- [ ] 8.4 Image upload + clear control per section/item; reorder controls for sections and items; publish toggle

## 9. Navigation & wiring

- [ ] 9.1 Add localized "Atelier" link to `frontend/components/layout/Header.tsx` (all viewports)
- [ ] 9.2 Add localized "Atelier" link to `frontend/components/layout/Footer.tsx`
- [ ] 9.3 Add the nav/footer label strings to `frontend/messages/en.json` + `frontend/messages/bg.json`

## 10. Frontend tests & verification

- [ ] 10.1 Component tests (vitest): renderer dispatch by type, body paragraph/bullet rendering, placeholder when image missing
- [ ] 10.2 Verify deep link `/atelier#process` scrolls correctly after a reorder
- [ ] 10.3 Manual pass: owner uploads an image and reviews BG copy in admin; page renders EN and BG end-to-end
