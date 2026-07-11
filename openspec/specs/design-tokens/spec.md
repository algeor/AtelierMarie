## ADDED Requirements

### Requirement: Tailwind content paths configured for class scanning
The system SHALL configure Tailwind's `content` array in `tailwind.config.ts` to include:
- `./app/**/*.{js,ts,jsx,tsx}`
- `./components/**/*.{js,ts,jsx,tsx}`
- `./lib/**/*.{js,ts,jsx,tsx}`

This ensures the production build correctly purges unused classes without removing classes referenced in components.

#### Scenario: Production build retains used utility classes
- **WHEN** `npm run build` runs the Tailwind purge step
- **THEN** all utility classes referenced in app/, components/, and lib/ files are retained in the output CSS

#### Scenario: Unreferenced classes are purged
- **WHEN** a class like `bg-purple-500` is not used anywhere in the content paths
- **THEN** it is removed from the production CSS bundle

### Requirement: Brand color palette defined as Tailwind tokens
The system SHALL define the following color tokens in `tailwind.config.ts` under `theme.extend.colors`:
- `warm-ivory` (#FFFDF7) — page background
- `cream` (#FFF8F0) — card/surface background
- `champagne-beige` (#F5E6D3) — borders, dividers
- `dusty-pink` (#E8C4B8) — decorative accents (NOT for focus indicators or text)
- `soft-brown` (#7D6352) — body text (darkened from #8B6F5C to ensure ≥4.5:1 on cream)
- `charcoal` (#2D2D2D) — headings, high-emphasis text
- `muted-gold` (#C4A265) — button fills, border accents (NOT standalone text — see usage constraint)

**Usage constraint:** Muted-gold SHALL only be used as a background fill (with charcoal text on top) or as a border/decorative accent. It SHALL NOT be used as text color on warm-ivory or cream backgrounds (contrast ratio 2.37:1 fails WCAG AA). For text links, use charcoal with underline or soft-brown.

#### Scenario: Tailwind classes use brand tokens
- **WHEN** a developer writes `bg-warm-ivory` or `text-muted-gold` in a component
- **THEN** the compiled CSS produces the correct hex value

#### Scenario: Default palette remains accessible
- **WHEN** a developer uses standard Tailwind colors (e.g., `text-red-500`)
- **THEN** they still resolve correctly (brand tokens extend, not replace, defaults)

#### Scenario: Body text meets contrast on all backgrounds
- **WHEN** soft-brown text (#7D6352) is rendered on cream (#FFF8F0)
- **THEN** the contrast ratio is at least 4.5:1 (WCAG AA compliant)

### Requirement: Typography scale with brand fonts via CSS variables
The system SHALL configure fonts using the `next/font/google` built-in module (NOT the deprecated `@next/font` package) with CSS variable output:

1. Instantiate Playfair Display with `variable: '--font-heading'`
2. Instantiate Inter with `variable: '--font-body'`
3. Apply both variable classes to the `<html>` element in root layout
4. Configure Tailwind fontFamily to reference CSS variables:
   - `fontFamily.heading`: `['var(--font-heading)', 'serif']`
   - `fontFamily.body`: `['var(--font-body)', 'sans-serif']`

The root layout SHALL apply `font-body` as the default body font and expose `font-heading` as a utility class for headings.

**Weight subsetting:** Only the required weights SHALL be loaded:
- Playfair Display: weights [400, 700] (regular and bold headings)
- Inter: weights [400, 500, 600, 700] (body text, medium labels, semibold UI, bold emphasis)

**Heading scale:** The root layout or `globals.css` SHALL define base heading styles in `@layer base`:
- `h1`: font-heading, text-3xl (1.875rem), leading-tight (1.25)
- `h2`: font-heading, text-2xl (1.5rem), leading-tight (1.25)
- `h3`: font-heading, text-xl (1.25rem), leading-snug (1.375)

These provide sensible defaults overrideable with utility classes.

#### Scenario: Heading font renders correctly
- **WHEN** an element has `className="font-heading"`
- **THEN** it renders in Playfair Display with serif fallback stack

#### Scenario: Body text defaults to Inter
- **WHEN** a page renders with no explicit font class
- **THEN** body text renders in Inter with sans-serif fallback stack

#### Scenario: No Flash of Unstyled Text
- **WHEN** the page first loads
- **THEN** fonts display with `font-display: swap` and are self-hosted (no external CDN requests)

#### Scenario: CSS variables bridge fonts to Tailwind
- **WHEN** Tailwind config references `var(--font-heading)`
- **THEN** it resolves to the next/font-generated font family string at runtime

### Requirement: Global base styles
The system SHALL provide `frontend/app/globals.css` with:
- Tailwind directives (`@tailwind base`, `components`, `utilities`)
- `body` background set to `warm-ivory`
- Default text color set to `soft-brown`
- Smooth scrolling enabled
- Antialiased text rendering
- `prefers-reduced-motion` override: `@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; scroll-behavior: auto !important; } }` — gracefully degrades ALL motion globally

#### Scenario: Fresh page has correct defaults
- **WHEN** the app renders with no additional styling
- **THEN** the background is #FFFDF7, text is #7D6352, and font is Inter

#### Scenario: Reduced motion is respected globally
- **WHEN** the user has `prefers-reduced-motion: reduce` enabled
- **THEN** all CSS animations (including `animate-pulse`, `animate-spin`) are suppressed

### Requirement: Semantic state colors
The system SHALL use the following semantic color pairings for status indicators (Badge, alerts, form validation). These reference Tailwind's default palette values but are documented here as part of the brand design system:

- `success`: green-100 bg (#DCFCE7) / green-800 text (#166534) — contrast 6.49:1 ✅ AA
- `warning`: amber-100 bg (#FEF3C7) / amber-800 text (#92400E) — contrast 6.37:1 ✅ AA
- `error`: red-50 bg (#FEF2F2) / red-700 text (#B91C1C) — contrast 6.14:1 on cream ✅ AA
- `accent`: muted-gold bg (#C4A265) / charcoal text (#2D2D2D) — contrast 5.71:1 ✅ AA

These colors are NOT added to `theme.extend.colors` (they already exist in Tailwind's default palette). They are documented here to establish approved pairings with verified contrast ratios.

#### Scenario: Success badge meets contrast
- **WHEN** `<Badge variant="success">` renders with green-100 bg and green-800 text
- **THEN** the contrast ratio is at least 4.5:1 (WCAG AA compliant)

#### Scenario: Warning badge meets contrast
- **WHEN** `<Badge variant="warning">` renders with amber-100 bg and amber-800 text
- **THEN** the contrast ratio is at least 4.5:1 (WCAG AA compliant)

### Requirement: Spacing and border-radius tokens
The system SHALL extend Tailwind's theme with:
- `borderRadius.brand`: 8px (default component radius)
- `borderRadius.pill`: 9999px (badge/tag radius)

#### Scenario: Brand radius applies to components
- **WHEN** a component uses `rounded-brand`
- **THEN** it renders with 8px border-radius

### Requirement: Transition tokens for consistent motion
The system SHALL extend Tailwind's theme with:
- `transitionDuration.fast`: 150ms (hover states, focus rings)
- `transitionDuration.normal`: 300ms (color transitions, layout shifts)
- `transitionTimingFunction.brand`: cubic-bezier(0.4, 0, 0.2, 1) (smooth luxury feel)

Components SHALL use `duration-fast` for hover/focus and `duration-normal` for state changes.

#### Scenario: Hover transitions use consistent timing
- **WHEN** a Button or Input receives a hover/focus state change
- **THEN** the transition uses `duration-fast` (150ms) with the brand easing function
