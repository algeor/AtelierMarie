## ADDED Requirements

### Requirement: Office list API endpoint
The system SHALL expose `GET /v1/delivery/offices` accepting query parameters `courier` (required, "speedy" or "econt"), `city` (required, string), and `type` (optional, "office" or "apt" to filter by staffed offices or lockers). The endpoint SHALL return a JSON array of office objects matching the given courier and city (case-insensitive match), optionally filtered by type.

#### Scenario: Fetch Speedy offices in Sofia
- **WHEN** client sends `GET /v1/delivery/offices?courier=speedy&city=София`
- **THEN** the response is HTTP 200 with an array of Speedy offices and lockers located in София, each containing id, name, type, city, address, and working_hours

#### Scenario: Fetch only lockers in Sofia
- **WHEN** client sends `GET /v1/delivery/offices?courier=speedy&city=София&type=apt`
- **THEN** the response is HTTP 200 with only automated parcel terminals (type "apt") in София

#### Scenario: Fetch Econt offices in Plovdiv
- **WHEN** client sends `GET /v1/delivery/offices?courier=econt&city=Пловдив`
- **THEN** the response is HTTP 200 with an array of Econt offices in Пловдив

#### Scenario: Invalid courier parameter
- **WHEN** client sends `GET /v1/delivery/offices?courier=dhl&city=София`
- **THEN** the response is HTTP 422 with validation error indicating courier must be "speedy" or "econt"

#### Scenario: Missing required parameters
- **WHEN** client sends `GET /v1/delivery/offices` without courier or city
- **THEN** the response is HTTP 422 with validation errors for missing required parameters

#### Scenario: No offices found for city
- **WHEN** client sends `GET /v1/delivery/offices?courier=speedy&city=НесъществуващоСело`
- **THEN** the response is HTTP 200 with an empty array

### Requirement: Cities list API endpoint
The system SHALL expose `GET /v1/delivery/cities` accepting query parameters `courier` (required, "speedy" or "econt") and `q` (optional, search prefix). The endpoint SHALL return a JSON array of distinct city names where the specified courier has offices, filtered by the search prefix (case-insensitive).

#### Scenario: List all Speedy cities
- **WHEN** client sends `GET /v1/delivery/cities?courier=speedy`
- **THEN** the response is HTTP 200 with a sorted array of all city names where Speedy has offices

#### Scenario: Search cities with prefix
- **WHEN** client sends `GET /v1/delivery/cities?courier=econt&q=Со`
- **THEN** the response is HTTP 200 with city names starting with "Со" (e.g., "София", "Созопол") where Econt has offices

#### Scenario: No cities match prefix
- **WHEN** client sends `GET /v1/delivery/cities?courier=speedy&q=xyz`
- **THEN** the response is HTTP 200 with an empty array

### Requirement: Office data stored as static JSON
The system SHALL load office data from static JSON files (`data/speedy_offices.json` and `data/econt_offices.json`) at application startup. The data SHALL be held in memory for fast filtering. Each office record SHALL contain: id (string, courier's own identifier), name (string, display name in Bulgarian), type (string, "office" or "apt"), city (string), address (string, street address), and working_hours (string, human-readable schedule).

#### Scenario: Application starts with office data
- **WHEN** the application starts and the JSON files exist in the data directory
- **THEN** office data is loaded into memory and available for the offices/cities endpoints

#### Scenario: Missing office data file
- **WHEN** the application starts and a courier JSON file is missing
- **THEN** the application logs a warning and the corresponding courier endpoints return empty arrays (not a startup failure)

### Requirement: Office data response shape
The system SHALL return office objects with the following fields: id (string), name (string), type (string, "office" or "apt"), city (string), address (string), working_hours (string). No additional fields SHALL be exposed.

#### Scenario: Office object structure
- **WHEN** client fetches offices and results are found
- **THEN** each object in the array contains exactly: id, name, type, city, address, working_hours — all as non-null strings

#### Scenario: Locker type indicator
- **WHEN** client fetches offices and a result is an automated parcel terminal
- **THEN** that object has type "apt" and the UI can display a locker icon and self-service pickup instructions

### Requirement: Office data sourced via fetch script
The system SHALL include a script (`scripts/fetch_courier_offices.py`) that fetches office data from official courier APIs (Econt NomenclaturesService.getOffices, Speedy POST /location/office), normalizes into the unified schema, and writes the JSON data files. The script SHALL be runnable manually for data refresh.

#### Scenario: Fetch script produces valid JSON
- **WHEN** `scripts/fetch_courier_offices.py` is run with valid courier API credentials
- **THEN** it produces `data/speedy_offices.json` and `data/econt_offices.json` with all offices including type field

#### Scenario: Fetch script handles API errors gracefully
- **WHEN** one courier API is unreachable during script execution
- **THEN** the script logs an error for that courier but still produces the JSON for the other courier if successful
