## ADDED Requirements

### Requirement: useAddToCart custom hook
A shared `useAddToCart` hook SHALL encapsulate the add-to-cart state machine (idle→loading→success→reset), and both `AddToCartButton` and `AddToCartSection` SHALL consume it instead of duplicating the logic.

#### Scenario: Adding item via AddToCartButton
- **WHEN** a user clicks AddToCartButton
- **THEN** the hook manages the loading→success→reset transitions and opens the cart drawer on success

#### Scenario: Adding item via AddToCartSection (PDP)
- **WHEN** a user clicks "Add to Cart" on the product detail page
- **THEN** the same hook manages identical state transitions, with the section providing quantity

### Requirement: Unified order status color map
A single exported `ORDER_STATUS_STYLES` constant SHALL define the color mapping for all order statuses, used by both `OrderStatusBadge` and the admin orders table.

#### Scenario: "shipped" status rendered in admin
- **WHEN** the admin orders page renders a "shipped" order
- **THEN** it SHALL use the same color as the customer-facing OrderStatusBadge (no divergence)

#### Scenario: New status added
- **WHEN** a developer adds a new order status color
- **THEN** they SHALL add it in one place and both admin and customer views reflect it

### Requirement: Replace inline button classes with Button component
Pages that render button-styled links SHALL use the existing `Button` component (or a link variant) instead of copy-pasting the full Tailwind class string.

#### Scenario: Orders page "Continue Shopping" link
- **WHEN** the orders page renders a link styled as a button
- **THEN** it SHALL use the `Button` component with `as="a"` or equivalent, not an inline class string

### Requirement: Use next/image for user avatars
The `UserMenu` and account page SHALL render user avatar images using `next/image` (with appropriate `sizes` and `alt` attributes) instead of raw `<img>` tags.

#### Scenario: Google avatar displayed in header
- **WHEN** a logged-in user's avatar appears in the header
- **THEN** it SHALL be rendered via `next/image` with width, height, sizes, and alt text

### Requirement: Use cn() utility for all className composition
Components SHALL use the project's `cn()` utility (clsx + tailwind-merge) for conditional/computed classNames, not template-literal interpolation.

#### Scenario: StatusTimeline conditional styling
- **WHEN** `StatusTimeline` applies conditional classes based on step completion
- **THEN** it SHALL use `cn('base-class', condition && 'conditional-class')` pattern

### Requirement: Use Input component in checkout form
The checkout page email/address inputs SHALL use the existing `Input` component from `components/ui/Input` instead of hand-rolled styled `<input>` elements.

#### Scenario: Checkout email field with validation error
- **WHEN** the checkout form shows an email validation error
- **THEN** it SHALL render the `Input` component with its built-in error state styling
