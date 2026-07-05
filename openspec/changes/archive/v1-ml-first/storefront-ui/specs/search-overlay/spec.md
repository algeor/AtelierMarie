# Search Overlay — Spec

## ADDED Requirements

### Requirement: Search Overlay Trigger and Display

A full-screen or modal search interface provides focused product discovery without navigating away from the current page.

#### Scenario: Search overlay opens from header icon

WHEN a user clicks the search icon in the header
THEN a full-screen (or large modal) search overlay appears
AND the overlay has a semi-transparent dark background
AND the search input field is auto-focused (cursor ready for typing)
AND the body scroll is locked
AND the overlay fades in with a smooth transition (200ms)

#### Scenario: Search overlay closes

WHEN a user clicks the close (X) button in the overlay
THEN the overlay fades out and disappears
WHEN a user presses the Escape key
THEN the overlay closes
WHEN a user clicks the semi-transparent background area (outside the search content)
THEN the overlay closes
AND body scroll is restored in all cases

#### Scenario: Search overlay is accessible via keyboard

WHEN the search overlay is open
THEN focus is trapped within the overlay (Tab cycles through overlay elements only)
AND the close button is reachable via Tab
AND pressing Escape closes the overlay and returns focus to the search icon in the header

### Requirement: Live Product Suggestions with Debounce

As the user types, product suggestions appear with a debounce to avoid excessive API calls.

#### Scenario: Suggestions appear after typing with debounce

WHEN a user types at least 2 characters in the search input
THEN after a 300ms pause in typing (debounce), a request is made to GET /v1/products/search?q={query}
AND matching product results are displayed below the input
AND each result shows product name, price, and thumbnail image
AND results are clickable, navigating to the product's PDP

#### Scenario: Suggestions update as user continues typing

WHEN a user modifies their search query
THEN the previous debounce timer resets
AND after 300ms of no further typing, a new search request is made
AND displayed results update to match the new query

#### Scenario: No results state

WHEN a search query returns zero results from the API
THEN a message is displayed: "No products found for '{query}'"
AND a suggestion to try different keywords is shown

#### Scenario: Loading state during fetch

WHEN a search request is in-flight
THEN a subtle loading indicator (spinner or skeleton) is shown in the results area
AND previous results remain visible until new results arrive (no flash of empty state)

### Requirement: Trending Products on Empty Input

When the search input is empty, trending products are shown to inspire discovery.

#### Scenario: Trending products displayed on overlay open

WHEN the search overlay opens and the input is empty
THEN trending products are fetched from GET /v1/recommendations/trending
AND they are displayed as a list or grid with the heading "Trending now"
AND each trending product shows name, price, and thumbnail

#### Scenario: Trending products replaced by search results

WHEN the user starts typing and results return
THEN the trending products section is replaced by live search results
WHEN the user clears the input (backspace to empty)
THEN trending products reappear

### Requirement: Search Event Emission

Search activity is tracked for analytics.

#### Scenario: search_query event is emitted on search

WHEN a search request completes (after debounce fires and results return)
THEN a search_query event is emitted
AND the event payload includes: query (the search text) and result_count (number of results returned)

#### Scenario: Event is not emitted for empty queries

WHEN the search input is empty or has fewer than 2 characters
THEN no search_query event is emitted
AND no API request is made
