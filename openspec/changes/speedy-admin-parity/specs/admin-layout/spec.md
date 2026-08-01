## ADDED Requirements

### Requirement: Admin navigation includes Speedy
The admin layout sidebar SHALL include a Speedy navigation item linking to `/admin/speedy`. The active link styling SHALL apply when the admin is on the Speedy page or nested Speedy admin routes.

#### Scenario: Speedy nav item visible
- **WHEN** an authenticated admin views the admin sidebar
- **THEN** the sidebar includes a Speedy link

#### Scenario: Speedy nav item navigates
- **WHEN** an admin clicks the Speedy link
- **THEN** the browser navigates to `/admin/speedy`
- **AND** the Speedy link is visually active
