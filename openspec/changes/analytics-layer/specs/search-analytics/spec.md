## ADDED Requirements

### Requirement: Search terms materialized table
The analytics layer SHALL compute an `analytics_search_terms` table in DuckDB containing aggregated search query statistics from the last 30 days.

The table MUST include: `query` (normalized/lowercased), `search_count`, and `avg_result_count`.

#### Scenario: Search terms normalized for aggregation
- **WHEN** the analytics job runs
- **AND** search events contain queries "Vanilla", "vanilla", and "VANILLA"
- **THEN** these are aggregated as a single row with query="vanilla" and search_count=3

#### Scenario: Average result count computed
- **WHEN** the analytics job runs
- **AND** "lavender" was searched 4 times with result_counts [10, 8, 12, 10]
- **THEN** avg_result_count equals 10.0

#### Scenario: Zero-result searches included
- **WHEN** search events have result_count=0 in metadata
- **THEN** those searches appear with their avg_result_count reflecting the zeros

#### Scenario: Only top results materialized
- **WHEN** the analytics job runs
- **THEN** `analytics_search_terms` contains at most the top 100 search terms by frequency (to bound table size)
