## ADDED Requirements

### Requirement: Speedy office data can be refreshed from official Location Service
The courier office refresh tooling SHALL support refreshing Speedy office and locker data from official Speedy Location Service APIs and writing the normalized `data/speedy_offices.json` file used by checkout and delivery endpoints.

#### Scenario: Refresh Speedy offices
- **WHEN** the office refresh script runs with valid Speedy credentials
- **THEN** it fetches Speedy office data from official Speedy APIs and writes normalized Speedy office records with id, name, type, city, address, and working hours

#### Scenario: Speedy office refresh failure is isolated
- **WHEN** Speedy office refresh fails but Econt refresh succeeds
- **THEN** the script reports the Speedy failure and still preserves or writes Econt data according to the existing refresh behavior

#### Scenario: Admin sees office refresh status
- **WHEN** a Speedy office refresh has recently succeeded or failed
- **THEN** the Speedy admin page can display the last refresh timestamp and status without blocking checkout
