# 2026-08-15 Fulfillment Review Notes

Scope reviewed:
- crafted-later checkout and fulfillment state handling
- admin fulfillment-ready workflow
- ledger/inventory visibility for partial backorders

Findings:
- Fixed: `mark_order_fulfillment_ready()` accepted cancelled/completed orders and could re-allocate stock after cancellation.
- Fixed: cancelling an `awaiting_production` order left the order stuck in that state, which was misleading and enabled the invalid admin action above.
- Fixed: admin inventory context reported partially backordered ledger items as `issued` instead of `awaiting_production`, hiding unfinished fulfillment work.
- Fixed: ledger cancellation now reverses each recorded `sale_issue` movement individually so crafted-later allocations preserve reversal lineage.

Follow-up verification added:
- order-service tests for cancelled crafted-later orders and invalid fulfillment-ready transitions
- inventory integration test for partial backorder visibility
- inventory integration test for multi-allocation cancellation reversal lineage
