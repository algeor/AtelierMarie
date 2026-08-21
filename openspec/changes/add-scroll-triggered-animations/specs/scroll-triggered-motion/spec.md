## ADDED Requirements

### Requirement: Reusable scroll reveal primitive
The system SHALL provide a reusable frontend primitive that reveals content once when it enters the viewport using a fade and small slide transition.

#### Scenario: Content reveals when visible
- **WHEN** a reveal-wrapped element enters the viewport threshold
- **THEN** the element transitions from hidden offset state to visible final state without changing its reserved layout space

#### Scenario: Repeated items reveal with stagger
- **WHEN** repeated reveal-wrapped items enter the viewport together
- **THEN** each item MAY use a short stagger delay based on its index while capping the delay to avoid slow lists

#### Scenario: Revealed content remains visible
- **WHEN** an element has already revealed and later leaves the viewport
- **THEN** it remains in its visible state instead of replaying repeatedly

### Requirement: Reduced motion fallback
The system SHALL respect `prefers-reduced-motion: reduce` for all scroll-triggered motion.

#### Scenario: Reduced motion renders final state
- **WHEN** the user has reduced motion enabled
- **THEN** reveal-wrapped elements render visible with no slide, fade, delay, or transition

#### Scenario: Content is usable without IntersectionObserver
- **WHEN** `IntersectionObserver` is unavailable
- **THEN** reveal-wrapped content renders in its final visible state

### Requirement: Reusable count-up metric primitive
The system SHALL provide a reusable frontend primitive that counts numeric metric values up when the metric enters the viewport.

#### Scenario: Numeric metric counts up once
- **WHEN** a count-up metric with numeric value enters the viewport
- **THEN** it animates from zero or a configured start value to the final value once

#### Scenario: Formatted metric preserves final display
- **WHEN** a count-up metric represents currency, percentages, or localized integers
- **THEN** the final rendered text matches the existing formatted metric display

#### Scenario: Non-numeric metric stays static
- **WHEN** a metric value is non-numeric status text
- **THEN** the system renders the text unchanged and does not run count-up animation

#### Scenario: Reduced motion count-up fallback
- **WHEN** the user has reduced motion enabled
- **THEN** count-up metrics render their final values immediately
