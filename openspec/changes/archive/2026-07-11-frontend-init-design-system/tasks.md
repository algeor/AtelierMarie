## 1. Install Dependencies

- [x] 1.1 Add tailwindcss, postcss, autoprefixer to devDependencies
- [x] 1.2 Add clsx and tailwind-merge to dependencies
- [x] 1.3 Run npm install and verify lockfile updates

## 2. Tailwind Configuration

- [x] 2.1 Create `frontend/tailwind.config.ts` with content paths (`./app/**/*.{js,ts,jsx,tsx}`, `./components/**/*.{js,ts,jsx,tsx}`, `./lib/**/*.{js,ts,jsx,tsx}`) and brand color palette (warm-ivory, cream, champagne-beige, dusty-pink, soft-brown #7D6352, charcoal, muted-gold)
- [x] 2.2 Add fontFamily.heading (`['var(--font-heading)', 'serif']`) and fontFamily.body (`['var(--font-body)', 'sans-serif']`) referencing CSS variables
- [x] 2.3 Add borderRadius.brand (8px) and borderRadius.pill (9999px) to config
- [x] 2.4 Create `frontend/postcss.config.js` with tailwindcss and autoprefixer plugins

## 3. Font Setup

- [x] 3.1 Configure Playfair Display with `variable: '--font-heading'` and Inter with `variable: '--font-body'` via `next/font/google` in root layout
- [x] 3.2 Apply both font variable classes (e.g., `${playfair.variable} ${inter.variable}`) to the `<html>` element
- [x] 3.3 Verify fonts load with `font-display: swap` and no external CDN requests

## 4. Global Styles

- [x] 4.1 Create `frontend/app/globals.css` with Tailwind directives and base layer styles
- [x] 4.2 Set body defaults: bg-warm-ivory, text-soft-brown, font-body, antialiased, smooth scroll
- [x] 4.3 Add `@media (prefers-reduced-motion: reduce)` rule to disable all animations (`.animate-pulse, .animate-spin { animation: none; }`)
- [x] 4.4 Import globals.css in root layout

## 5. Layout Metadata

- [x] 5.1 Export `metadata` from root layout with `title: { template: '%s | Atelier Marie', default: 'Atelier Marie' }` and a default description

## 6. Utility Function

- [x] 6.1 Create `frontend/lib/utils.ts` with `cn()` helper (clsx + tailwind-merge)

## 7. Base UI Components

- [x] 7.1 Create `frontend/components/ui/Button.tsx` — primary/secondary/ghost variants, sm/md/lg sizes, isLoading with inline SVG spinner, `aria-busy`/`aria-disabled` for loading, `focus-visible:ring-2 ring-soft-brown ring-offset-2`, min 44px touch target
- [x] 7.2 Create `frontend/components/ui/Input.tsx` — `<label htmlFor>` with auto-generated `useId()`, error state with `aria-invalid` + `aria-describedby` + error icon, `focus-visible:ring-2 ring-soft-brown ring-offset-2`, extends native input
- [x] 7.3 Create `frontend/components/ui/Badge.tsx` — default (champagne-beige bg, charcoal text for contrast), accent/success/warning variants, pill shape
- [x] 7.4 Create `frontend/components/ui/Skeleton.tsx` — animated pulse placeholder with `prefers-reduced-motion` support (static when reduced), className control

## 8. Verification

- [x] 8.1 Create a temporary demo page (`frontend/app/design-system/page.tsx`) rendering all components in all states — marked with `// TODO: Remove after visual verification`
- [x] 8.2 Run `npm run build` to verify Tailwind purge works and no compile errors
- [x] 8.3 Visual check: colors, fonts, component states, focus rings, and reduced-motion behavior render correctly
