## MODIFIED Requirements

### Requirement: Managed announcement bar
The global storefront layout SHALL render the existing top announcement bar from the managed site banner API instead of hardcoded static copy. The announcement bar SHALL appear above the header when the public banner endpoint returns an active banner, and SHALL be hidden when no banner is active. The bar SHALL display localized message text, optional link label and URL, and a dismiss control.

Dismissal SHALL be keyed by the banner's public dismiss key, not a single static storage key, so updated banner content or schedule can be shown even if a user dismissed an older banner. The banner SHALL remain responsive and SHALL NOT overlap header controls on mobile or desktop.

#### Scenario: Active managed banner renders above header
- **WHEN** the public banner endpoint returns an active banner
- **THEN** the announcement bar renders above the header with the localized message

#### Scenario: No active banner hides bar
- **WHEN** the public banner endpoint returns `banner = null`
- **THEN** no announcement bar is rendered

#### Scenario: Banner link renders when configured
- **WHEN** the active banner response includes `link_url` and `link_label`
- **THEN** the announcement bar renders a link using those values

#### Scenario: Dismissal is scoped to banner version
- **WHEN** a user dismisses banner version A and an admin later publishes banner version B
- **THEN** banner version B is shown to that user despite the prior dismissal

#### Scenario: Announcement bar remains responsive
- **WHEN** the banner renders on mobile, tablet, or desktop widths
- **THEN** message text, optional link, and dismiss control do not overlap and remain readable/clickable
