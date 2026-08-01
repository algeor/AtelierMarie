## MODIFIED Requirements

### Requirement: Office data stored as static JSON
The system SHALL load office data from static JSON files (`data/speedy_offices.json` and `data/econt_offices.json`) at application startup. The data SHALL be held in memory for fast filtering. Each office record SHALL contain: id (string, stable internal identifier), name (string, display name in Bulgarian), type (string, "office" or "apt"), city (string), address (string, street address), working_hours (string, human-readable schedule), and code (string or null). For Econt offices, `code` SHALL preserve Econt's native office code used by Econt label/return APIs.

#### Scenario: Application starts with office data
- **WHEN** the application starts and the JSON files exist in the data directory
- **THEN** office data is loaded into memory and available for the offices/cities endpoints

#### Scenario: Missing office data file
- **WHEN** the application starts and a courier JSON file is missing
- **THEN** the application logs a warning and the corresponding courier endpoints return empty arrays (not a startup failure)

#### Scenario: Econt office data includes native code
- **WHEN** Econt office data is normalized from official Econt nomenclature data
- **THEN** each Econt office record preserves the courier-native `code` separately from the internal `id`

### Requirement: Office data response shape
The system SHALL return office objects with the following fields: id (string), name (string), type (string, "office" or "apt"), city (string), address (string), working_hours (string), and code (string or null). Econt office responses SHALL include the native Econt office code when known so checkout can persist it for later fulfillment and return handling.

#### Scenario: Office object structure
- **WHEN** client fetches offices and results are found
- **THEN** each object in the array contains id, name, type, city, address, working_hours, and code fields

#### Scenario: Econt office response exposes code
- **WHEN** client fetches Econt offices and a matching office has a native Econt code
- **THEN** the response includes `code` with that native Econt office code

#### Scenario: Locker type indicator
- **WHEN** client fetches offices and a result is an automated parcel terminal
- **THEN** that object has type "apt" and the UI can display a locker icon and self-service pickup instructions

### Requirement: Office data sourced via fetch script
The system SHALL include a script (`scripts/fetch_courier_offices.py` or the current courier-office normalization script) that fetches office data from official courier APIs (Econt NomenclaturesService.getOffices, Speedy POST /location/office), normalizes into the unified schema, preserves Econt native office codes, and writes the JSON data files. The script SHALL be runnable manually for data refresh.

#### Scenario: Fetch script produces valid JSON
- **WHEN** the courier office fetch/normalization script is run with valid courier API data
- **THEN** it produces `data/speedy_offices.json` and `data/econt_offices.json` with all offices including type field and Econt code field where available

#### Scenario: Fetch script handles API errors gracefully
- **WHEN** one courier API is unreachable during script execution
- **THEN** the script logs an error for that courier but still produces the JSON for the other courier if successful
