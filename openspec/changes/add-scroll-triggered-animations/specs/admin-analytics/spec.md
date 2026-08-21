## ADDED Requirements

### Requirement: Admin analytics metric count-up
The admin analytics page SHALL count up numeric metric card values when the metrics enter the viewport while preserving existing number, percentage, currency, and status formatting.

#### Scenario: Analytics numbers count up
- **WHEN** analytics summary metrics enter the viewport
- **THEN** numeric session, event, order, and revenue values animate to their final formatted values once

#### Scenario: Percent values preserve suffix
- **WHEN** a conversion metric with a percentage enters the viewport
- **THEN** the number counts up and the percent suffix remains present in the final display

#### Scenario: Non-numeric health status stays static
- **WHEN** the analytics health metric value is status text
- **THEN** the health text renders unchanged and does not animate as a number

#### Scenario: Analytics reduced motion fallback
- **WHEN** reduced motion is enabled
- **THEN** analytics metric cards render their final values immediately without count-up animation
