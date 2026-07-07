## Why

The frontend shell exists (Next.js 14 scaffolded with types, mock-api, and api facade), but has no visual layer — no Tailwind, no design tokens, no base components. Every future page (product grid, cart drawer, checkout) depends on a consistent design system being in place first. This is the visual foundation that unblocks all UI work.

## What Changes

- Install and configure Tailwind CSS with custom design tokens (luxury palette: warm-ivory through muted-gold)
- Set up Google Fonts (Playfair Display headings, Inter body) via the built-in `next/font/google` module
- Build reusable base UI components: `Button` (primary/secondary/ghost), `Input`, `Badge`, `Skeleton`
- Verify existing `frontend/lib/types.ts`, `mock-api.ts`, and `api.ts` are complete and aligned with backend Pydantic models (they already exist from prior setup)

## Capabilities

### New Capabilities
- `design-tokens`: Tailwind config with brand colors, typography scale (via CSS variables), spacing, border-radius, content paths, and reduced-motion support
- `base-ui-components`: Foundational UI primitives (Button, Input, Badge, Skeleton) with full WCAG AA accessibility (ARIA attributes, focus management, contrast compliance)

### Modified Capabilities

_(none — no existing spec-level behavior changes)_

## Impact

- **New files:** `frontend/tailwind.config.ts`, `frontend/postcss.config.js`, `frontend/app/globals.css`, `frontend/lib/utils.ts`, `frontend/components/ui/Button.tsx`, `Input.tsx`, `Badge.tsx`, `Skeleton.tsx`
- **Modified:** `frontend/package.json` (add tailwindcss, postcss, autoprefixer, clsx, tailwind-merge), `frontend/app/layout.tsx` (fonts, metadata, globals.css import)
- **Dependencies:** Tailwind CSS 3.4+, clsx, tailwind-merge. Fonts use the built-in `next/font/google` (no additional package needed).
- **No backend changes.** No API changes. No breaking changes.
