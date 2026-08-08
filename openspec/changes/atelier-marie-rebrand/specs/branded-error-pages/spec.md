## ADDED Requirements

### Requirement: Branded public 404 page
The system SHALL render a dedicated Atelier Marie 404 page for localized storefront not-found routes. The page SHALL use the rebrand palette, oversized elegant serif typography for `404` and `Not Found`, a soft product or atelier visual accent, and a primary `Back to Home` action.

#### Scenario: Not-found page renders brand recovery
- **WHEN** a visitor opens a missing localized storefront route
- **THEN** the page displays a branded 404 message with a visible localized `Back to Home` action
- **AND** the page does not expose technical stack traces or raw framework error text

#### Scenario: Not-found page is mobile usable
- **WHEN** the 404 page is viewed on a mobile viewport
- **THEN** `404`, `Not Found`, the short recovery message, and the primary action are visible without a long scroll

### Requirement: Branded generic UI error page
The system SHALL render a branded generic error page for unexpected frontend failures. The page SHALL use calmer typography than the 404 page, show `Something went wrong.`, provide a primary `Back to Home` action, and provide `Try Again` only where retrying is technically possible.

#### Scenario: Runtime error page renders safe recovery copy
- **WHEN** a localized storefront route hits a frontend runtime error boundary
- **THEN** the user sees a branded generic error message and recovery action
- **AND** no internal exception details are shown to shoppers

#### Scenario: Retry action appears only when available
- **WHEN** the error boundary provides a retry/reset callback
- **THEN** the page shows a `Try Again` action
- **AND** when retry/reset is unavailable the page does not show a fake retry action

### Requirement: Error pages preserve accessibility and contrast
The branded error pages SHALL preserve keyboard access, visible focus states, readable contrast, localized metadata where applicable, and reduced-motion behavior.

#### Scenario: Error recovery actions are accessible
- **WHEN** a keyboard user tabs through the error page
- **THEN** all recovery actions receive visible focus and can be activated by keyboard

#### Scenario: Error page respects reduced motion
- **WHEN** the user has `prefers-reduced-motion: reduce` enabled
- **THEN** decorative error-page motion is disabled or reduced without hiding content
