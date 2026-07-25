## ADDED Requirements

### Requirement: Social media icon links in footer
The system SHALL display Instagram and TikTok icon links in the footer that open the Atelier Marie social profiles in new browser tabs.

#### Scenario: Social icons render in footer
- **WHEN** any localized storefront page loads
- **THEN** the footer contains Instagram and TikTok icon links

#### Scenario: Instagram link uses confirmed Atelier Marie profile
- **WHEN** the Instagram icon link renders without an overriding environment value
- **THEN** its `href` is `https://www.instagram.com/atelier_marie25?igsh=MWQ1YzA4aHF2a3Q4MA==`

#### Scenario: TikTok link uses confirmed Atelier Marie profile
- **WHEN** the TikTok icon link renders without an overriding environment value
- **THEN** its `href` is `https://www.tiktok.com/@ateliermarie25?_r=1&_t=ZN-98H9buODbdu`

#### Scenario: Social URLs are configurable
- **WHEN** `NEXT_PUBLIC_INSTAGRAM_URL` or `NEXT_PUBLIC_TIKTOK_URL` is set
- **THEN** the corresponding footer link uses the configured public URL instead of the default

#### Scenario: Social links open safely in new tabs
- **WHEN** the Instagram and TikTok links render
- **THEN** each anchor includes `target="_blank"` and `rel="noopener noreferrer"`

#### Scenario: Social links are accessible
- **WHEN** a screen reader encounters the Instagram or TikTok icon link
- **THEN** each link has a descriptive accessible label naming the destination

#### Scenario: Social links support touch and keyboard use
- **WHEN** a user navigates the footer by touch or keyboard
- **THEN** each social icon link has at least a 44x44px target and a visible focus state

#### Scenario: Social icons match the existing footer design
- **WHEN** the footer renders the social icons
- **THEN** the icons use the existing footer color/focus/hover conventions rather than introducing a new visual style
