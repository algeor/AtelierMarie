## MODIFIED Requirements

### Requirement: Responsive admin layout
The system SHALL provide a mobile-first admin layout that works on phone, tablet, and desktop. On mobile, admin workflows SHALL use simple navigation, single-column forms, reachable filters/actions, and mobile-friendly list/card alternatives for dense tables. On larger screens, the layout MAY expand into sidebar/table patterns without changing available functionality.

#### Scenario: Mobile admin navigation is usable
- **WHEN** an admin opens `/admin` or an admin subpage on a mobile viewport
- **THEN** navigation to all existing admin sections remains reachable without horizontal squeezing

#### Scenario: Desktop sidebar expanded
- **WHEN** viewport width is >= 1024px
- **THEN** sidebar or equivalent desktop navigation shows full navigation labels and active state

#### Scenario: Tablet and small desktop navigation remains clear
- **WHEN** viewport width is between mobile and desktop breakpoints
- **THEN** admin navigation adapts without overlapping content or hiding available sections

#### Scenario: Mobile forms are single column
- **WHEN** an admin edits products, content, legal pages, settings, or similar form-heavy admin pages on mobile
- **THEN** labels, inputs, errors, and save actions are arranged in a readable single-column flow

## ADDED Requirements

### Requirement: Admin rebrand preserves existing admin tools
The admin rebrand SHALL preserve every already exposed admin module, route, action, setting, validation state, loading state, empty state, and error state. Visual simplification SHALL group or collapse advanced controls rather than remove them.

#### Scenario: Admin routes remain reachable
- **WHEN** an authenticated admin opens the rebranded admin navigation
- **THEN** existing admin routes for dashboard, products, orders, inventory, accounting, analytics, content/FAQ, legal/privacy/cookies/terms, delivery/couriers, promotions, and payment settings remain reachable where they already exist

#### Scenario: Advanced controls are not removed
- **WHEN** an admin page is simplified for mobile
- **THEN** existing advanced actions remain available through clear grouping, tabs, drawers, or collapsible sections

### Requirement: Admin uses minimal useful motion
Admin UI motion SHALL be minimal and functional. Allowed motion includes drawer open/close, focus/hover feedback, save confirmation, loading indicators, and small state transitions. Admin SHALL NOT use scroll-driven storytelling, parallax, decorative reveals, or playful motion.

#### Scenario: Admin avoids decorative storefront motion
- **WHEN** an admin page renders
- **THEN** it does not use public-storefront decorative animations such as hero reveals, parallax, category line-draw loops, or footer wordmark reveals

#### Scenario: Admin respects reduced motion
- **WHEN** an admin user has `prefers-reduced-motion: reduce` enabled
- **THEN** nonessential admin motion is disabled or reduced while feedback remains understandable

### Requirement: Admin visual style is quieter than storefront
The admin UI SHALL use the Atelier Marie token system with quieter surface, text, border, and action choices. It SHALL prioritize readability, compact repeated work, visible status/action feedback, and low visual clutter over editorial composition.

#### Scenario: Admin pages avoid marketing layout patterns
- **WHEN** an admin page renders
- **THEN** it does not use oversized hero sections, decorative product imagery, nested cards, or marketing-style composition for routine tools
