# Frontend Patterns

Use this when touching `frontend/`.

## The Shape

```text
frontend/app/[locale]/       Locale-prefixed pages
frontend/components/         Reusable UI and feature components
frontend/contexts/           App-wide state: auth, cart, admin, cookie consent
frontend/lib/types.ts        TypeScript mirror of backend Pydantic models
frontend/lib/api-client.ts   Real API client
frontend/lib/mock-api.ts     Mock dev API
frontend/lib/api.ts          Switches real/mock by env
frontend/messages/           en/bg translation catalogs
frontend/i18n/               next-intl routing setup
```

## Locale Routing

All customer/admin pages are under:

```text
/en/...
/bg/...
```

Rules:

- Add user-visible strings to both `messages/en.json` and `messages/bg.json`.
- Do not hardcode product/category names in the frontend.
- API calls should carry locale where the backend needs localized content.
- Use the project navigation helpers from `frontend/i18n/`.

## API Contract Rule

When backend response shape changes, update all of these together:

1. `app/models/*.py`
2. `frontend/lib/types.ts`
3. `frontend/lib/api-client.ts`
4. `frontend/lib/mock-api.ts`
5. Component/page tests

Skipping the mock API is a common way to make local frontend dev lie.

## Contexts

- `CartContext`: global cart state and drawer refreshes.
- `AuthContext`: logged-in user state and logout/login refresh.
- `AdminContext`: admin guard/state, built on auth/admin checks.
- `CookieConsentContext`: analytics consent. Tracking must check this.

Do not make checkout depend on analytics consent.

## Component Areas

- `components/ui`: base primitives like Button, Input, Badge, Skeleton.
- `components/products`: cards, gallery, comments, reactions, price display, video.
- `components/cart`: cart drawer, item rows, add-to-cart, badge.
- `components/checkout`: delivery selector, courier comparison, shipping price summary.
- `components/admin`: product form, sidebar, FAQ/story/taxonomy managers.
- `components/layout`: header, footer, language toggle, announcement/cookie controls.

## Admin Pages

Admin routes live under:

```text
frontend/app/[locale]/admin/
```

Current admin pages cover:

- dashboard
- products
- orders
- delivery
- promotions
- taxonomy
- FAQ
- atelier/about story
- analytics

Admin UI should use existing admin components and shared status badges. Do not invent new status colors unless the shared mapping is missing a real state.

## Storefront Pages

Current customer pages include:

- homepage
- product listing and detail
- checkout
- order confirmation, retry payment, order history/detail
- account
- contact
- FAQ
- atelier/about
- terms, privacy, cookies

## Styling Rules

- Use the existing Tailwind tokens and `cn()` helper.
- Use shared UI components before raw button/input styling.
- Keep loading, empty, and error states explicit.
- Product images should use the existing media helpers/components.
- Keep bilingual text lengths in mind. Bulgarian strings often need more room.

## Tracking Rule

Frontend tracking lives in `frontend/lib/analytics.ts` and `frontend/lib/tracking.ts`.

Rules:

- Track only after consent.
- Tracking failures must not block UI.
- Checkout must still work with analytics off.

