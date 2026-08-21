## ADDED Requirements

### Requirement: Admin dashboard metric count-up
The admin dashboard SHALL count up numeric stat card values when the cards enter the viewport while preserving existing labels, icons, and final values.

#### Scenario: Numeric stat cards count up
- **WHEN** admin dashboard stats load and their cards enter the viewport
- **THEN** numeric values animate from zero or a configured start value to their final value once

#### Scenario: Loading skeletons remain unchanged
- **WHEN** admin dashboard stats are still loading
- **THEN** existing stat-card skeleton placeholders render instead of count-up values

#### Scenario: Dashboard reduced motion fallback
- **WHEN** reduced motion is enabled
- **THEN** stat cards render final numeric values immediately without count-up animation
