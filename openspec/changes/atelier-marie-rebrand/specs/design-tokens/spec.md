## MODIFIED Requirements

### Requirement: Brand color palette defined as Tailwind tokens
The system SHALL define the Atelier Marie rebrand palette in one central token layer and expose semantic usage tokens for components. Palette values SHALL be easy to customize without editing individual components.

Default brand palette values SHALL include:
- `soft-blush` (#ECC6C6)
- `coral-dream` (#F0CCD0)
- `muted-rose` (#DBAAAC)
- `vintage-mauve` (#C28E8D)
- `dusty-terra` (#B27474)
- `warm-clay` (#A15958)
- `soft-off-white` (#EEEFE9)
- `warm-cream` (#E7D9CC)
- `sand-taupe` (#BBA58E)
- `sage` (#959D90)
- `dark-brown` (#513D34)
- `deep-green-black` (#223030)

Semantic tokens SHALL cover page background, surface, elevated surface, primary text, muted text, border, primary action, secondary action, accent, focus ring, success, warning, and error. Components SHOULD use semantic tokens instead of raw palette tokens unless the palette token is purely decorative.

#### Scenario: Tailwind classes use rebrand tokens
- **WHEN** a developer uses a configured brand utility class or semantic token utility
- **THEN** the compiled CSS resolves to the centrally defined rebrand value

#### Scenario: Palette values can be changed centrally
- **WHEN** a brand color is updated in the central token definition
- **THEN** components using semantic tokens pick up the new value without component-level color edits

#### Scenario: Body text meets contrast on all backgrounds
- **WHEN** primary or muted text renders on approved page and surface backgrounds
- **THEN** the contrast ratio meets WCAG AA for normal text unless the text is decorative and nonessential

#### Scenario: Palette avoids one-note color usage
- **WHEN** a rebranded storefront surface uses blush or rose as the main brand warmth
- **THEN** neutral backgrounds and deep green-black, dark brown, sage, or clay semantic tokens provide readable contrast and visual depth
- **AND** the surface does not rely only on variations of a single pink tone for structure, text, and actions

## ADDED Requirements

### Requirement: Components avoid hardcoded color values
The frontend SHALL avoid hardcoded hex, rgb, hsl, and one-off Tailwind color values in rebranded components when a semantic token exists. Exceptions SHALL be documented inline or centralized when a third-party integration or browser-native control requires a literal value.

#### Scenario: Rebrand color audit catches literal values
- **WHEN** a rebrand implementation pass is reviewed
- **THEN** hardcoded component color values are either removed, replaced by tokens, or documented as intentional exceptions

### Requirement: Admin uses quieter semantic token choices
The admin UI SHALL use the same base palette system as the storefront but map admin surfaces to quieter, more functional semantic values. Admin tokens SHALL prioritize readability, dense repeated use, and clear status/action feedback over editorial decoration.

#### Scenario: Admin palette remains aligned but practical
- **WHEN** an admin page renders after the rebrand
- **THEN** it uses Atelier Marie semantic colors while keeping forms, tables, filters, and status messages readable and practical
