# Analytics Layer — Proposal

## Summary

Introduce a shared analytics layer that materializes event aggregates into DuckDB tables, consumed by multiple services (ML recommendations, admin dashboard, storefront). Eliminates duplicate computation where both ML and admin independently aggregate the same events table.

## Problem

The current design has two independent compute paths producing overlapping aggregates:
- **ML batch job** (every 30 min): rebuilds `features_item_popularity`, `features_cooccurrence`, `features_ctr`, `features_session_sequences` from the events table
- **Admin dashboard** (per-request + 5-min cache): runs aggregate queries for product views, session counts, conversion rates, search terms — many of which duplicate ML feature computation

This means:
1. Same DuckDB scans run twice with different schedules
2. Two caching strategies for the same underlying data
3. Two lock coordination patterns (`.batch.lock` + `.ml-compute.lock`)
4. Adding a new metric consumer requires building yet another query path

## Solution

A single **analytics compute job** that materializes shared tables in DuckDB at two refresh tiers:
- **Tier 1 (every 5 min):** Cheap aggregates — product metrics, session metrics, search terms, funnel/conversion
- **Tier 2 (every 30 min):** Expensive ML features — co-occurrence, session sequences, CTR, popularity scores

All consumers (ML recommendations, admin dashboard, storefront "trending" badges) read from pre-materialized `analytics_*` tables instead of running their own queries.

## Scope

**In scope:**
- Unified batch compute job with tiered refresh
- 8 materialized DuckDB tables (`analytics_*` prefix)
- SQL-as-files for auditability and testability
- Single `.batch.lock` coordination (replaces `.ml-compute.lock`)
- Compute scheduler (5-min loop with 30-min tier2 gate)

**Out of scope:**
- Point-in-time feature versioning (not needed)
- Real-time/streaming aggregates
- External feature store tooling (Feast, Tecton)
- Custom date-range pre-computation (admin falls through to direct query for non-default ranges)

## Dependencies

**Depends on:**
- `event-ingestion-pipeline` (events table in DuckDB must exist)
- `session-identity` (session_identity table for session metrics)

**Depended on by:**
- `ml-recommendations` (reads analytics tables for ranking)
- `admin-dashboard` (reads analytics tables for metrics)
- `storefront-ui` (can read trending/popular for badges)
- `maintenance-tooling` (needs to know about analytics tables for rebuild/vacuum)

## Constraints

- Zero additional infrastructure (no Redis, no external services)
- Must complete Tier 1 rebuild in <5 seconds for <1M events
- Must complete Tier 2 rebuild in <60 seconds for <1M events
- Single `.batch.lock` serializes all DuckDB writes (event loader, session flush, analytics compute)
- Analytics compute uses non-blocking lock with wait (up to 60s timeout)
