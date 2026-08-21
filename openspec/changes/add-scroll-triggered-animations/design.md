## Context

The frontend is a Next.js app with server-rendered pages and client components where interaction is needed. Motion already exists in `frontend/app/globals.css` through classes such as `.landing-scroll-reveal`, `.featured-preview-card`, `.editorial-image-settle`, and global `prefers-reduced-motion` handling. Some card components already carry reveal-like class names, but there is no consistent viewport trigger for all sections and no reusable numeric count-up behavior.

This change is frontend-only. It should improve perceived polish on public browsing pages and admin metric surfaces without changing data contracts, URLs, or CMS/admin content models.

## Goals / Non-Goals

**Goals:**

- Provide one reusable way to reveal sections and repeated cards when they enter the viewport.
- Provide one reusable way to count numeric metrics up when visible.
- Apply reveals to homepage, product listing, and atelier/about section cards using existing visual language.
- Apply count-up behavior to admin dashboard and analytics metric blocks.
- Keep motion tasteful, short, staggered, and disabled for users with reduced-motion preferences.
- Avoid layout shift: elements reserve their normal space before animation starts.

**Non-Goals:**

- No backend changes, database changes, or new admin configuration fields.
- No page redesign or new content sections.
- No dependency on a large animation framework unless implementation proves the local hook/CSS approach insufficient.
- No count-up for non-numeric status values such as analytics health strings.

## Decisions

### Use a shared IntersectionObserver hook plus lightweight components

Create a small client-side primitive such as `useInViewOnce()` in `frontend/lib/` or `frontend/components/motion/`, then expose components like `ScrollReveal` and `CountUpMetric`. The hook observes an element, marks it visible once, and disconnects after activation.

Alternatives considered:
- CSS `animation-timeline: view()` only: elegant, but browser support is uneven and existing behavior needs a JS fallback for reliable count-up triggers.
- Framer Motion or another animation dependency: powerful, but unnecessary for simple fade/slide and number interpolation.

### Keep reveal styling in CSS and activation in React

Use CSS classes for opacity, transform, transition duration, easing, and stagger values. React should only add a visible class or data attribute when the element enters the viewport. This aligns with the existing `globals.css` motion layer and avoids scattering animation constants across components.

Alternatives considered:
- Inline animation styles everywhere: faster to add in one component, but inconsistent and harder to audit for reduced motion.
- Tailwind-only utility strings: possible for static motion, but less useful for reusable viewport states and stagger patterns.

### Count up only from parsed numeric values or explicit numbers

Prefer passing numeric values and formatters into `CountUpMetric`, especially for admin stats and analytics cards. Where current code has already formatted strings, keep the final visible output identical by separating `value`, `suffix`, `prefix`, or a formatter function.

Alternatives considered:
- Parse every display string: brittle for currencies, percentages, localized separators, and labels.
- Animate all metric text: would make non-numeric statuses look broken.

### Respect reduced motion at both CSS and JS levels

CSS must render reveal targets visible with no transform under `prefers-reduced-motion: reduce`. JS count-up should skip animation and render the final value immediately when reduced motion is active.

Alternatives considered:
- CSS-only reduced-motion suppression: sufficient for transforms, but JS counters would still animate unless explicitly guarded.

## Risks / Trade-offs

- Hydration mismatch risk if animated values render different text on server and client -> render the final value until the client hook starts, or keep count-up components client-only with stable final fallback semantics.
- Too much motion could feel busy on product grids -> use once-only reveals, small translations, short durations, and stagger caps.
- IntersectionObserver tests can be flaky in jsdom -> mock the observer and separately test formatting/reduced-motion paths.
- Count-up parsing can break localized output -> pass numeric inputs and explicit formatters instead of deriving values from display strings.

## Migration Plan

1. Add the shared motion hook/component primitives.
2. Replace direct `.landing-scroll-reveal` usage in target card/section components with the shared reveal primitive or a consistent `data-visible` class contract.
3. Update admin metric components to accept optional numeric count-up inputs while keeping string values supported.
4. Add focused tests for viewport activation, reduced-motion fallback, and metric formatting.
5. Roll back by removing wrapper usage; all content remains rendered because the animation layer is presentational only.

## Open Questions

- Should count-up metrics be public-facing too if a future homepage section contains numeric stats?
- Should reveal animations replay when an element leaves and re-enters the viewport, or remain once-only? Current proposal chooses once-only to avoid distraction.
