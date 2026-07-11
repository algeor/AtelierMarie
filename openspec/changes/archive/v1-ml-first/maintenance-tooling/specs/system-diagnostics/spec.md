## ADDED Requirements

### Requirement: Storage diagnostics
The system SHALL report storage usage including buffer file count, archive file count and total size, DuckDB file size, SQLite file size, and available disk space when the diagnose command is executed.

#### Scenario: Storage section reported
- **WHEN** the diagnose command is executed
- **THEN** the output SHALL include a Storage section showing: buffer files count, archive files count and total size, DuckDB size, SQLite size, and disk free space with percentage

### Requirement: DuckDB diagnostics
The system SHALL report DuckDB database statistics including total event count, latest event timestamp, active session count, and expired session count.

#### Scenario: DuckDB statistics reported
- **WHEN** the diagnose command is executed AND DuckDB is accessible
- **THEN** the output SHALL include total events, timestamp of the most recent event, count of active sessions (is_expired=FALSE), and count of expired sessions (is_expired=TRUE)

#### Scenario: DuckDB inaccessible
- **WHEN** the diagnose command is executed AND DuckDB cannot be opened
- **THEN** the output SHALL indicate DuckDB is inaccessible with the error message

### Requirement: SQLite diagnostics
The system SHALL report SQLite database statistics including user count, active product count, inactive product count, and order count.

#### Scenario: SQLite statistics reported
- **WHEN** the diagnose command is executed AND SQLite is accessible
- **THEN** the output SHALL include: user count, active product count, inactive product count, and total order count

### Requirement: Service status diagnostics
The system SHALL check and report the running status of system services: API server, batch loader, ML compute, and session expiry.

#### Scenario: Running services detected
- **WHEN** the diagnose command is executed AND services are running
- **THEN** each running service SHALL be reported with its PID and uptime or last-run timestamp

#### Scenario: Stopped services flagged
- **WHEN** the diagnose command is executed AND a service is not running
- **THEN** that service SHALL be flagged with a warning indicator

### Requirement: Issue detection
The system SHALL identify potential issues based on diagnostic data and report them with severity indicators (warning or OK).

#### Scenario: Buffer file accumulation warning
- **WHEN** the diagnose command is executed AND more than 1 buffer file exists between batch cycles
- **THEN** a warning SHALL be displayed indicating unexpected buffer file accumulation

#### Scenario: Stale latest event warning
- **WHEN** the diagnose command is executed AND the most recent event is older than 10 minutes
- **THEN** a warning SHALL be displayed indicating the event pipeline may be stalled

#### Scenario: All checks pass
- **WHEN** the diagnose command is executed AND no issues are detected
- **THEN** a summary line SHALL indicate all checks passed
