## ADDED Requirements

### Requirement: Social media icon links in footer
The system SHALL display Instagram and TikTok icon links in the footer that open the Atelier Marie social profiles in new browser tabs.

#### Scenario: Social icons render in footer
- **WHEN** any page loads
- **THEN** the footer contains Instagram and TikTok icons (SVG) wrapped in anchor links

#### Scenario: Instagram link opens in new tab
- **WHEN** a visitor clicks the Instagram icon
- **THEN** a new browser tab opens navigating to the configured Instagram URL (`NEXT_PUBLIC_INSTAGRAM_URL`)

#### Scenario: TikTok link opens in new tab
- **WHEN** a visitor clicks the TikTok icon
- **THEN** a new browser tab opens navigating to the configured TikTok URL (`NEXT_PUBLIC_TIKTOK_URL`)

#### Scenario: Social links have security attributes
- **WHEN** the Instagram and TikTok links render
- **THEN** each anchor element includes `target="_blank"` and `rel="noopener noreferrer"`

#### Scenario: Social links are accessible
- **WHEN** a screen reader encounters the Instagram or TikTok icon link
- **THEN** each link has a descriptive accessible label via `aria-label` ("Follow us on Instagram", "Follow us on TikTok")

#### Scenario: Social URLs are configurable
- **WHEN** `NEXT_PUBLIC_INSTAGRAM_URL` and `NEXT_PUBLIC_TIKTOK_URL` are set
- **THEN** the Instagram and TikTok links use those values as their `href` values

#### Scenario: Social icons match design system
- **WHEN** the footer renders the social icons
- **THEN** each icon uses the `text-warm-gray-400` color, transitions to `text-gold-400` on hover, and has a minimum touch target of 44x44px
