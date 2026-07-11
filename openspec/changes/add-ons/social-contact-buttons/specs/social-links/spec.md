## ADDED Requirements

### Requirement: Instagram icon link in footer
The system SHALL display an Instagram icon link in the footer that opens the Atelier Marie Instagram profile in a new browser tab.

#### Scenario: Instagram icon renders in footer
- **WHEN** any page loads
- **THEN** the footer contains an Instagram icon (SVG) wrapped in an anchor link

#### Scenario: Instagram link opens in new tab
- **WHEN** a visitor clicks the Instagram icon
- **THEN** a new browser tab opens navigating to the configured Instagram URL (`NEXT_PUBLIC_INSTAGRAM_URL`)

#### Scenario: Instagram link has security attributes
- **WHEN** the Instagram link renders
- **THEN** the anchor element includes `target="_blank"` and `rel="noopener noreferrer"`

#### Scenario: Instagram link is accessible
- **WHEN** a screen reader encounters the Instagram icon link
- **THEN** the link has an accessible label ("Follow us on Instagram" via `aria-label`)

#### Scenario: Instagram URL is configurable
- **WHEN** the environment variable `NEXT_PUBLIC_INSTAGRAM_URL` is set
- **THEN** the Instagram link uses that URL as its `href` value

#### Scenario: Instagram icon matches design system
- **WHEN** the footer renders the Instagram icon
- **THEN** the icon uses the `text-warm-gray-400` color, transitions to `text-gold-400` on hover, and has a minimum touch target of 44×44px
