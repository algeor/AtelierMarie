## 1. Database Migration

- [x] 1.1 Rename `name` → `name_en` and `description` → `description_en` in products table
- [x] 1.2 Add `name_bg TEXT` and `description_bg TEXT` columns to products table
- [x] 1.3 Add `translation_stale_bg INTEGER DEFAULT 0` and `translation_stale_en INTEGER DEFAULT 0` columns to products table
- [x] 1.4 Add `preferred_locale TEXT DEFAULT 'en'` column to sessions table
- [x] 1.5 Create Bulgarian FTS5 virtual table (`products_fts_bg`) with triggers on `name_bg`/`description_bg`
- [x] 1.6 Update existing FTS5 triggers to use `name_en`/`description_en` column names
- [x] 1.7 Update `database.py` schema creation to include new columns and FTS table

## 2. Backend API Changes

- [x] 2.1 Update product Pydantic models: add `name_bg`, `description_bg`, `translation_stale_bg`, `translation_stale_en` fields
- [x] 2.2 Add locale-aware response model (public API returns `name`/`description` based on requested locale)
- [x] 2.3 Update `product_service.py` to accept `locale` parameter and return locale-appropriate content with fallback
- [x] 2.4 Update `product_service.py` search to query locale-appropriate FTS index
- [x] 2.5 Update product routes: add `locale` query parameter to `GET /v1/products` and `GET /v1/products/{id}`
- [x] 2.6 Update admin product routes: accept dual-language fields on create/update
- [x] 2.7 Implement staleness flag logic in admin service (set stale on one-side update, clear on update of stale side)
- [x] 2.8 Update CSV import to support `name_en`, `name_bg`, `description_en`, `description_bg` columns
- [x] 2.9 Add `preferred_locale` to session middleware (store detected/updated locale in session row)
- [x] 2.10 Update seed script to populate both language fields (or just EN with BG as NULL)

## 3. Frontend Restructure (Locale Routing)

- [x] 3.1 Install `next-intl` (or chosen i18n library)
- [x] 3.2 Create `frontend/messages/en.json` with all extracted English UI strings
- [x] 3.3 Create `frontend/messages/bg.json` with Bulgarian translations of all UI strings
- [x] 3.4 Create `frontend/middleware.ts` with locale detection (Accept-Language + cookie) and redirect logic
- [x] 3.5 Move all routes under `frontend/app/[locale]/` dynamic segment
- [x] 3.6 Update root layout to set `<html lang={locale}>` dynamically
- [x] 3.7 Configure `next-intl` provider in `[locale]/layout.tsx`
- [x] 3.8 Update `next.config.js` with i18n configuration if required by library

## 4. Frontend Translation Integration

- [x] 4.1 Update Header component to use translation keys for "Home", "Shop"
- [x] 4.2 Update Footer component to use translation keys
- [x] 4.3 Update AnnouncementBar to use translation keys
- [x] 4.4 Update product components (ProductCard, AddToCartSection, etc.) to use translation keys
- [x] 4.5 Update cart components (CartDrawer, CartItem) to use translation keys
- [x] 4.6 Update checkout components to use translation keys
- [x] 4.7 Update order components to use translation keys
- [x] 4.8 Update auth components (LoginButton, UserMenu) to use translation keys
- [x] 4.9 Update admin components to use translation keys
- [x] 4.10 Create error code → localized message mapping for API error display

## 5. Language Toggle Component

- [x] 5.1 Create `LanguageToggle` component (flag icon showing opposite locale)
- [x] 5.2 Implement click handler: navigate to equivalent page in other locale
- [x] 5.3 Set `NEXT_LOCALE` cookie on toggle click
- [x] 5.4 Send locale preference update to backend (update session row)
- [x] 5.5 Add `LanguageToggle` to Header (right side, next to auth/cart)
- [x] 5.6 Ensure toggle remains visible on mobile viewport (not collapsed)

## 6. Font & Styling

- [x] 6.1 Update font imports to include `cyrillic` subset: `subsets: ["latin", "cyrillic"]`
- [x] 6.2 Verify Cyrillic rendering across heading and body fonts

## 7. Admin Bilingual UI

- [x] 7.1 Update ProductForm to show dual-language input fields (name_en/name_bg, description_en/description_bg)
- [x] 7.2 Add staleness indicator (⚠️ badge) next to fields flagged as stale
- [x] 7.3 Update admin API client to send/receive dual-language fields
- [x] 7.4 Update CSV import UI to document new column format

## 8. SEO

- [x] 8.1 Add `hreflang` alternate link tags to all pages (pointing to the other locale version)
- [x] 8.2 Generate dual-locale sitemap (entries for both `/bg/` and `/en/` versions)
- [x] 8.3 Add 301 redirects from old non-prefixed URLs to `/en/` equivalents

## 9. Testing

- [x] 9.1 Add backend tests: locale-aware product retrieval (both languages, fallback)
- [x] 9.2 Add backend tests: staleness flag logic (set, clear, both-side update)
- [x] 9.3 Add backend tests: FTS search per locale
- [x] 9.4 Add backend tests: CSV import with dual-language columns
- [x] 9.5 Add backend tests: session `preferred_locale` persistence
- [x] 9.6 Add frontend tests: middleware locale detection and redirect
- [x] 9.7 Add frontend tests: language toggle navigation and cookie update
- [x] 9.8 Add frontend tests: translation rendering (spot-check key components in both locales)
- [x] 9.9 Verify all existing tests pass with locale prefix (update route paths in test fixtures)
