## ADDED Requirements

### Requirement: Admin navigation includes analytics
The admin layout sidebar SHALL include an Analytics navigation item linking to `/admin/analytics`. The active link styling SHALL apply when the admin is on the analytics page.

#### Scenario: Analytics nav item visible
- **WHEN** an authenticated admin views the admin sidebar
- **THEN** the sidebar includes an Analytics link

#### Scenario: Analytics nav item navigates
- **WHEN** an admin clicks the Analytics link
- **THEN** the browser navigates to `/admin/analytics`
- **AND** the Analytics link is visually active
