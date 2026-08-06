# Admin Panel Redesign Notes

Date: 2026-08-02

## Direction

- Make the admin panel smoother, glassier, and more polished.
- Add subtle animations, especially slide-in behavior for admin categories.
- Make it feel like "candy" while keeping it practical for daily admin work.
- Ask before editing code.

## Guardrails

- Preserve all existing admin routes, tools, actions, settings, filters, loading states, empty states, and errors.
- Visual changes must not remove or hide functionality.
- Admin motion should stay useful: drawer transitions, category slide-ins, hover/focus feedback, loading states, and save confirmations.
- Respect reduced-motion preferences.
- Keep admin quieter and more functional than storefront pages.

## Orders Filter Issue

The Admin Orders filters currently take too much vertical space because each group is shown as many pill buttons.

Current groups:

- Order progress: All, Pending, Confirmed, Shipped, Delivered, Return in transit, Returned, Cancelled
- Payment status: All, Awaiting payment, Paid, Pay on delivery, Payment failed, Refunded
- Payment method: All, Card, Cash on delivery, Bank transfer
- Accounting filter: All, Missing document, Unresolved exception, Payout does not match, Delivery payment pending, Missing refund document, VAT review, Missing batch, Missing movement, Missing sold cost, Stock value warning, Return inventory review

## Preferred Filter Layout

- Replace the pill groups with a compact filter toolbar.
- Use four separate dropdowns:
  - Order progress
  - Payment status
  - Payment method
  - Accounting filter
- Layout:
  - Desktop: four dropdowns in one row.
  - Tablet: two columns.
  - Mobile: one column.
- Keep the info icon beside each label.
- Add a small Reset filters button.
- Keep selected values visible in the dropdowns.
- Avoid extra active-filter chips unless selected filters become hard to notice.

## Dropdown Aesthetic

Native browser selects do not fit the Atelier Marie admin aesthetic and can look too OS-default.

Preferred solution:

- Build a reusable custom `AdminSelect` component.
- Use a styled button trigger instead of raw native select UI.
- Trigger styling:
  - cream or glass surface
  - soft border
  - subtle shadow
  - 8px rounded corners
  - selected value text
  - chevron icon
- Floating menu styling:
  - rounded panel
  - cream/glass background
  - soft shadow
  - gentle hover highlight
  - checkmark for selected option

## Accessibility Requirements For `AdminSelect`

- Enter or Space opens the menu.
- Arrow keys move through options.
- Escape closes the menu.
- Click outside closes the menu.
- Focus state is visible.
- Reduced-motion mode disables nonessential motion.

## Reuse Opportunity

If implemented, `AdminSelect` should become the standard admin dropdown for:

- Admin Orders filter toolbar.
- Per-row order status updates.
- Payment settings dropdowns.
- Accounting and inventory filters.
- Other admin pages currently using native selects where visual consistency matters.

## Testing Notes

- Update tests that currently expect filter pill buttons.
- Preserve the existing `getAdminOrders` filter arguments.
- Verify desktop, tablet, and mobile layouts.
- Verify keyboard operation and focus states.
