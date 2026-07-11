## Context

The Next.js 14 project exists at `frontend/` with App Router, TypeScript, and the API layer (`lib/types.ts`, `lib/mock-api.ts`, `lib/api.ts`) already scaffolded. However, there is no CSS framework, no design tokens, and no reusable components. Tailwind CSS is the standard utility-first framework for Next.js projects and aligns with the rapid iteration goals of a small-team e-commerce build.

The brand identity targets a luxury artisan aesthetic: warm neutrals, serif headings, generous whitespace, and subtle interactions. All future pages (product grid, cart drawer, checkout, admin) depend on these foundational tokens and primitives.

## Goals / Non-Goals

**Goals:**
- Install Tailwind CSS 3.4 and configure custom design tokens (colors, typography, spacing)
- Integrate Google Fonts (Playfair Display, Inter) via `next/font/google` for zero-FOUT loading
- Create 4 base UI primitives: Button, Input, Badge, Skeleton — all WCAG AA accessible
- Establish component file conventions (`frontend/components/ui/`)
- Ensure the design system renders correctly with no runtime JS issues

**Non-Goals:**
- Page layouts (Header, Footer, ProductCard) — those come in subsequent changes
- Accordion component — deferred to the product detail/FAQ phase where it is first needed
- Dark mode — not planned for MVP
- Component documentation / Storybook — premature for this stage
- Animation library (framer-motion) — defer until interaction patterns are solidified
- Icon system — use inline SVG or Lucide later
- Form components beyond Input (Textarea, Select) — deferred to checkout phase

**Follow-up (next phase prerequisites):**
- Textarea, Select, and form validation patterns must be added before checkout implementation begins
- Accordion needed before product detail/FAQ page

## Decisions

### 1. Tailwind 3.4 (not 4.x)

Tailwind 4.x is stable (v4.3.x) but uses a CSS-first config paradigm (no `tailwind.config.ts`). We choose 3.4 because: (a) `tailwind-merge` has comprehensive 3.x class resolution support; (b) extensive Next.js 14 documentation and examples target 3.x; (c) avoiding config migration cost for an initial 4-component system. Will re-evaluate at the product grid phase when more components exist.

**Alternative:** CSS Modules — rejected for velocity reasons; utility-first is faster for solo/small-team iteration.
**Alternative:** Tailwind 4.x — viable but config paradigm shift deferred to avoid scope creep in a foundational change.

### 2. `next/font/google` for font loading (built-in, no package install)

Next.js 14 built-in font optimization handles subsetting, self-hosting, and `font-display: swap` automatically. No external CDN calls, no FOUT. Fonts are exposed as CSS variables (`--font-heading`, `--font-body`) which Tailwind references in `fontFamily`.

**Alternative:** Manual `@font-face` in CSS — more setup, no subsetting optimization, must handle preload manually.
**Note:** The deprecated `@next/font` package is NOT used — `next/font/google` is built into Next.js 14.

### 3. Component API: `className` prop + `cn()` utility

Components accept a `className` prop merged via a `cn()` helper (clsx + tailwind-merge). This allows composition without style leakage.

```ts
// lib/utils.ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }
```

**Alternative:** CVA (class-variance-authority) — powerful but overkill for 4 components. Can adopt later if variant matrix grows.

### 4. Component variants via props, not separate components

`<Button variant="primary" size="md">` rather than `<PrimaryButton>`, `<GhostButton>`. Keeps the API surface small and the import list short.

### 5. No component library dependency (no shadcn/ui, Radix) — for now

The design is highly custom (luxury brand). Starting from scratch with Tailwind ensures pixel-perfect control. For these 4 simple primitives, accessibility can be handled in-house (ARIA attributes, focus-visible, useId).

**Future:** Individual Radix primitives (Dialog, DropdownMenu, Combobox) SHOULD be adopted for complex interactive widgets (modals, dropdowns) when they are introduced in later phases. Building all ARIA patterns manually for complex widgets increases accessibility regression risk.

### 6. Component file conventions

- One component per file in `frontend/components/ui/`
- Named exports (not default): `export function Button(...)`
- No barrel `index.ts` file — import directly from component file (avoids circular deps, better tree-shaking)
- Co-located tests when testing framework is added: `Button.test.tsx` alongside `Button.tsx`

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Tailwind purge misses utility classes in dynamic strings | Use complete class names, never concatenate partials (e.g., `bg-${color}` is banned). Content paths configured for all source directories. |
| Font files increase bundle size | `next/font` auto-subsets to Latin glyphs only (~20KB per font) |
| Design tokens drift from spec | Tokens defined once in `tailwind.config.ts`, consumed everywhere via `theme()` |
| Component scope creep | Limit to 4 primitives. Complex components (Modal, Accordion) are separate changes |
| Building ARIA patterns manually increases a11y regression risk | Adopt Radix primitives for complex interactive widgets in later phases. Current primitives (Button, Input) are simple enough for in-house ARIA. |
| Color contrast issues with luxury palette | All text colors validated against WCAG AA (4.5:1). Muted-gold restricted to fills/borders only, never standalone text. |
