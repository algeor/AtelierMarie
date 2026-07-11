## ADDED Requirements

### Requirement: Button component with variants
The system SHALL provide a `<Button>` component at `frontend/components/ui/Button.tsx` supporting:
- **Variants:** `primary` (muted-gold bg, charcoal text), `secondary` (transparent bg, champagne-beige border, soft-brown text), `ghost` (no border, no bg, soft-brown text with hover underline)
- **Sizes:** `sm` (h-9, px-3, text-sm — desktop only), `md` (h-10, px-4, text-base), `lg` (h-12, px-6, text-lg)
- **Touch target:** All sizes SHALL have a minimum tappable area of 44px height. The `sm` variant uses `min-h-[44px]` on mobile viewports (<768px) or padding to expand the hit area.
- **Props:** Extends native `<button>` attributes plus `variant`, `size`, `isLoading`, `className`
- **Loading state:** When `isLoading=true`, the button SHALL show an inline SVG spinner (`animate-spin` class) and be disabled. The spinner is a simple circle/arc SVG defined within Button.tsx (no icon library dependency).
- **Disabled state:** Reduced opacity (0.6), cursor-not-allowed, no hover effects
- **Focus state:** All variants SHALL show a visible focus ring on `:focus-visible`: `focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory`. Minimum 3:1 contrast against surrounding background.

**Accessibility:**
- When `isLoading=true`: `aria-busy="true"`, `aria-disabled="true"`. Spinner element has `aria-hidden="true"`.
- When `disabled`: `aria-disabled="true"` (in addition to the native `disabled` attribute).
- Button text always serves as the accessible name.

#### Scenario: Primary button renders correctly
- **WHEN** `<Button variant="primary">Add to Cart</Button>` is rendered
- **THEN** it displays with muted-gold background, charcoal text, rounded-brand corners, and 44px minimum touch target height

#### Scenario: Loading state disables interaction and announces to screen readers
- **WHEN** `<Button isLoading>Processing</Button>` is rendered
- **THEN** the button shows an inline SVG spinning indicator, text remains visible, click events are suppressed, and `aria-busy="true"` is set

#### Scenario: Ghost button hover
- **WHEN** a user hovers over `<Button variant="ghost">`
- **THEN** the text color transitions to charcoal and an underline appears

#### Scenario: Custom className merges correctly
- **WHEN** `<Button className="mt-4 w-full">` is rendered
- **THEN** the additional classes merge with (and can override) the default styles without duplication

#### Scenario: Focus ring visible on keyboard navigation
- **WHEN** a user tabs to any Button variant
- **THEN** a 2px soft-brown ring with 2px offset appears around the button, clearly visible against the page background

### Requirement: Input component with label and error state
The system SHALL provide an `<Input>` component at `frontend/components/ui/Input.tsx` supporting:
- **Props:** Extends native `<input>` attributes plus `label`, `error`, `id`, `className`
- **Label:** Rendered as a `<label>` element in `text-sm font-medium text-soft-brown`. Uses `htmlFor` linked to the input's `id`. If no `id` prop is provided, auto-generates one via `useId()`.
- **Error state:** When `error` string is provided:
  - Border changes to `border-red-700`
  - Error message displays below in `text-sm text-red-700` (passes 4.5:1 on cream)
  - Input has `aria-invalid="true"`
  - Error message element has a generated `id` referenced by `aria-describedby` on the input
  - An error icon (inline SVG, `aria-hidden="true"`) appears before the error text as a non-color indicator
- **Focus state:** `focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2` (soft-brown provides ≥3:1 contrast on all backgrounds)
- **Default styling:** cream background, champagne-beige border, rounded-brand, h-10, px-3

#### Scenario: Input with label renders correctly with programmatic association
- **WHEN** `<Input label="Email" type="email" />` is rendered
- **THEN** a `<label>` element with "Email" text appears above the input, connected via `htmlFor`/`id`, and the input has cream background with champagne-beige border

#### Scenario: Error state displays validation message via multiple channels
- **WHEN** `<Input error="Email is required" />` is rendered
- **THEN** the input border changes to red-700, an error icon + "Email is required" appears below in red-700 text, `aria-invalid="true"` is set, and `aria-describedby` references the error message

#### Scenario: Focus ring visible on keyboard navigation
- **WHEN** user focuses the input via keyboard (tab)
- **THEN** a 2px soft-brown focus ring with offset appears around the input, clearly visible against warm-ivory and cream backgrounds

### Requirement: Badge component for status and category labels
The system SHALL provide a `<Badge>` component at `frontend/components/ui/Badge.tsx` supporting:
- **Variants:**
  - `default` (champagne-beige bg, **charcoal** text — ensures ≥4.5:1 contrast at text-xs)
  - `accent` (muted-gold bg, charcoal text)
  - `success` (green-100 bg, green-800 text)
  - `warning` (amber-100 bg, amber-800 text)
- **Props:** `variant`, `className`, `children`
- **Styling:** Inline-flex, rounded-pill, px-2.5, py-0.5, text-xs, font-medium

#### Scenario: Default badge renders with accessible contrast
- **WHEN** `<Badge>Floral</Badge>` is rendered
- **THEN** it displays as a small pill with champagne-beige background and charcoal text (contrast ≥4.5:1)

#### Scenario: Accent badge for featured items
- **WHEN** `<Badge variant="accent">Featured</Badge>` is rendered
- **THEN** it displays with muted-gold background and charcoal text

### Requirement: Skeleton component for loading placeholders
The system SHALL provide a `<Skeleton>` component at `frontend/components/ui/Skeleton.tsx` supporting:
- **Props:** `className` (for width/height control), no required props
- **Styling:** Animated pulse, champagne-beige background, rounded-brand by default
- **Reduced motion:** When `prefers-reduced-motion: reduce` is active, the pulse animation SHALL be suppressed and the component renders as a static champagne-beige block
- **Usage pattern:** Compose multiple Skeleton elements to mimic content layout during loading

#### Scenario: Skeleton with custom dimensions
- **WHEN** `<Skeleton className="h-4 w-32" />` is rendered
- **THEN** it displays a pulsing champagne-beige rectangle of 16px height and 128px width

#### Scenario: Skeleton for product card placeholder
- **WHEN** multiple Skeleton elements are composed (image area + text lines)
- **THEN** they pulse in sync with consistent timing to indicate loading state

#### Scenario: Reduced motion disables animation
- **WHEN** the user has `prefers-reduced-motion: reduce` enabled
- **THEN** the Skeleton renders as a static champagne-beige block with no animation

### Requirement: cn() utility for class merging
The system SHALL provide a `cn()` function at `frontend/lib/utils.ts` that:
- Accepts any number of class values (strings, arrays, conditionals)
- Merges them with Tailwind conflict resolution (later classes win)
- Uses `clsx` for conditional logic and `tailwind-merge` for deduplication
- Imported as `import { cn } from '@/lib/utils'`

#### Scenario: Conflicting Tailwind classes resolve correctly
- **WHEN** `cn("px-4", "px-6")` is called
- **THEN** it returns `"px-6"` (last value wins, no duplicates)

#### Scenario: Conditional classes work
- **WHEN** `cn("base", isActive && "text-charcoal", !isActive && "text-soft-brown")` is called
- **THEN** only the truthy class is included in the output string
