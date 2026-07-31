# Components, Pages, And Admin UI

This maps the frontend surface.

## Page Groups

Customer pages:

- `app/[locale]/page.tsx`: homepage
- `app/[locale]/products/page.tsx`: product listing
- `app/[locale]/products/[id]/page.tsx`: product detail
- `app/[locale]/checkout/page.tsx`: checkout
- `app/[locale]/orders/page.tsx`: order history
- `app/[locale]/orders/[id]/page.tsx`: order detail
- `app/[locale]/orders/[id]/confirmation/page.tsx`: confirmation
- `app/[locale]/orders/[id]/retry-payment/page.tsx`: card retry
- `app/[locale]/account/page.tsx`: account
- `app/[locale]/faq/page.tsx`: FAQ
- `app/[locale]/atelier/page.tsx`: story/about
- `app/[locale]/contact/page.tsx`: contact
- `app/[locale]/terms|privacy|cookies/page.tsx`: legal pages

Admin pages:

- `app/[locale]/admin/page.tsx`: dashboard
- `app/[locale]/admin/products/page.tsx`: products
- `app/[locale]/admin/products/new/page.tsx`: create product
- `app/[locale]/admin/orders/page.tsx`: orders
- `app/[locale]/admin/orders/[id]/page.tsx`: order detail
- `app/[locale]/admin/delivery/page.tsx`: delivery settings
- `app/[locale]/admin/promotions/page.tsx`: campaigns/banner
- `app/[locale]/admin/taxonomy/page.tsx`: taxonomy
- `app/[locale]/admin/faq/page.tsx`: FAQ manager
- `app/[locale]/admin/atelier/page.tsx`: atelier manager
- `app/[locale]/admin/analytics/page.tsx`: analytics reports

## Component Groups

| Folder | Purpose |
|---|---|
| `components/ui` | Shared primitives: Button, Input, Badge, Skeleton, Portal. |
| `components/layout` | Header, Footer, language toggle, announcement, cookie settings. |
| `components/products` | Cards, grids, detail, gallery, social, reactions, comments. |
| `components/cart` | Drawer, rows, add button, badge. |
| `components/checkout` | Delivery selection, courier comparison, shipping summary. |
| `components/orders` | Status badge and timeline. |
| `components/admin` | Admin guard/sidebar, product form, managers, ship modal. |
| `components/auth` | Login button, user avatar/menu. |
| `components/atelier` | Story/about renderers. |
| `components/faq` | FAQ accordion. |
| `components/contact` | Contact form. |

## Design System Rules

- Use shared `Button`, `Input`, `Badge`, and `Skeleton` when possible.
- Use `cn()` from `frontend/lib/utils.ts` for class composition.
- Keep loading/empty/error states explicit.
- Do not add one-off status colors if a shared status map exists.
- Keep text responsive. Bulgarian strings can be longer.

## Admin UI Rules

- Admin pages use the admin layout/sidebar.
- Admin actions must surface backend validation errors.
- Save/confirmation states should be visible.
- Mutating admin flows should refresh affected data.
- Backend auth remains authoritative.

## Product UI Rules

- Product listing uses managed taxonomy data.
- Product card price display must show effective price correctly.
- Product media should go through existing media helpers and gallery components.
- Product detail should show safety/care/compliance fields when available.
- Social comments/reactions should fail gracefully.

## Checkout UI Rules

- Preserve form input on validation/network errors.
- Show shipping price and total clearly.
- Do not trust frontend totals as payment proof.
- Card return page must fetch backend payment status.
- Cart should refresh after order creation/confirmation.

