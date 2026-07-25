# Checkout Flow — Dropped Layer-1 Guarantees

## Context

When `shipping-courier-integration` was archived (2026-07-25) and its delta specs
synced into `openspec/specs/`, the MODIFIED requirement **"Checkout converts cart
to order atomically"** was applied as a full replacement. The delta author's text
covered the new delivery/shipping scenarios but **did not carry forward three
Layer-1 scenarios** that existed in the prior canonical spec.

These scenarios were dropped from `openspec/specs/checkout-flow/spec.md`. The
production code very likely still implements all three — but the canonical spec no
longer documents them. This note preserves them so they can be re-incorporated into
a proper change (not silently restored into the canonical spec).

## Dropped Scenarios (verbatim from prior canonical spec)

These belong under **Requirement: Checkout converts cart to order atomically**.

### Scenario: Race condition — two checkouts for last item are serialized by BEGIN IMMEDIATE
- **WHEN** two concurrent sessions each have the last unit of product X in their cart and both attempt checkout simultaneously
- **THEN** the second transaction immediately receives SQLITE_BUSY (due to BEGIN IMMEDIATE lock), which results in HTTP 409; exactly one checkout succeeds, product X stock ends at 0, not negative

### Scenario: Checkout logs full operation lifecycle
- **WHEN** a checkout operation completes (success or failure)
- **THEN** structured logs are emitted with: operation start (session_id, item_count), stock validation result, and operation end (order_id or error type, duration_ms)

### Scenario: Database operational error during checkout is logged and reported
- **WHEN** a `sqlite3.OperationalError` occurs during checkout (e.g., disk full)
- **THEN** the transaction is rolled back, the error is logged at ERROR level with full context (session_id, operation="checkout", exc_info=True), and the API returns HTTP 500 with a generic error message (no internal details leaked)

## Why this matters

All three are Layer-1 (critical-path) guarantees:

- **BEGIN IMMEDIATE serialization** — the concurrency defense against negative stock
  on last-item races. Directly tied to the `CHECK (stock >= 0)` DB constraint.
- **Lifecycle logging** — observability for the checkout path.
- **OperationalError rollback/500** — ensures no internal details leak and the txn
  is rolled back on disk/lock errors.

## Open Questions / Next Step

1. Does the current code still implement all three? (Almost certainly yes — the
   sync only touched the spec, not the code. Verify against `order_service.py`.)
2. Restore path: create a small change that re-adds these three scenarios to the
   canonical `checkout-flow` spec as a MODIFIED requirement, so the spec matches the
   code again.
3. Consider whether the sync tooling should warn when a MODIFIED requirement's
   replacement text drops scenarios present in the target.
