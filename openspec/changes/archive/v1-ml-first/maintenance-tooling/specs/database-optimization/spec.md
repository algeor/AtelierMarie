## ADDED Requirements

### Requirement: DuckDB vacuum and optimization
The system SHALL execute VACUUM and ANALYZE on the DuckDB database when the vacuum command is executed, reclaiming space from deleted rows and updating query optimizer statistics.

#### Scenario: DuckDB vacuumed
- **WHEN** the vacuum command is executed
- **THEN** DuckDB SHALL be vacuumed and the size before and after SHALL be reported

#### Scenario: DuckDB analyzed
- **WHEN** the vacuum command is executed
- **THEN** ANALYZE SHALL be run on DuckDB to update query optimizer statistics

### Requirement: SQLite vacuum and optimization
The system SHALL execute VACUUM on the SQLite database when the vacuum command is executed, reclaiming space and rebuilding indexes.

#### Scenario: SQLite vacuumed
- **WHEN** the vacuum command is executed
- **THEN** SQLite SHALL be vacuumed and the size before and after SHALL be reported

### Requirement: Vacuum size change reporting
The system SHALL report the size change for each database after vacuum operations complete.

#### Scenario: Size reduction reported
- **WHEN** the vacuum command completes
- **THEN** stdout SHALL show: database name, size before, size after, and bytes freed for each database

### Requirement: Mutual exclusion during vacuum
The system SHALL acquire the maintenance file lock before performing vacuum operations.

#### Scenario: Lock prevents concurrent vacuum
- **WHEN** the vacuum command is executed AND another maintenance process holds the lock
- **THEN** the command SHALL exit with an error without performing any operations

#### Scenario: Lock acquired successfully
- **WHEN** the vacuum command is executed AND no other process holds the lock
- **THEN** the lock SHALL be acquired and vacuum operations SHALL proceed
