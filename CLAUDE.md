# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AtelierMarie is a luxury candle e-commerce platform with event-driven analytics, ML recommendations, and zero-budget infrastructure. It uses a dual-database architecture (SQLite for OLTP, DuckDB for OLAP) with a JSONL buffer layer between them.

**Status:** Planning phase complete; implementation not yet started beyond a skeleton FastAPI app in `main.py`.

## Technology Stack

- **Backend:** Python 3.11, FastAPI, Pydantic 2, Uvicorn
- **OLTP Database:** SQLite (WAL mode)
- **OLAP Database:** DuckDB (single-writer)
- **Frontend (planned):** Next.js 14, React Server Components, Tailwind CSS
- **Browser SDK (planned):** Vanilla JS (~5KB, zero-dependency)
- **Auth:** Google OAuth 2.0 + JWT (HS256)
- **Hosting:** Oracle Cloud Free Tier (single VPS), Nginx, systemd

## Development Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the backend (current skeleton)
uvicorn main:app --reload --port 8000

# Once implementation starts, the entrypoint will move:
# uvicorn app.main:app --reload --port 8000
```

Build configuration (pyproject.toml, requirements.txt, Makefile) does not exist yet — create it when beginning implementation.

## Architecture

See `ARCHITECTURE.md` for the full system design. Key points:

- **Anonymous-first:** Full cart/checkout works without login. Identity is an optional overlay linked at read-time via JOINs, never by mutating stored events.
- **Fire-and-forget events:** `POST /v1/events` returns 202 immediately; events write to daily JSONL files (`O_APPEND` atomic). A batch loader moves them into DuckDB every 60 seconds.
- **Dual-database split:** SQLite handles transactional data (products, orders, users, cart). DuckDB handles analytics (events, ML features, session identity).
- **File-lock coordination:** No Redis/Kafka. Concurrency uses `fcntl.flock` with lock files (`.batch.lock`, `.ml-compute.lock`, `.maintenance.lock`).
- **Fallback chains:** Recommendations degrade gracefully: ML → popularity → manual picks → random.

## Planned Application Structure

```
app/
├── main.py              # App factory + lifespan (background jobs)
├── config.py            # pydantic-settings (env vars)
├── constants.py         # Lock paths, timeouts, limits
├── database.py          # SQLite + DuckDB connection management
├── middleware/session.py
├── models/              # Pydantic schemas (shared contracts)
├── routes/              # FastAPI routers (thin — delegate to services)
├── services/            # Business logic (testable, no HTTP concerns)
├── jobs/                # Background tasks (batch_loader, ml_compute, session_expiry)
└── maintenance/         # CLI module (cleanup, GDPR, rebuild, diagnostics)
```

## Implementation Plan

See `IMPLEMENTATION_PLAN.md`. Designed for two parallel developers over 7 sprints (~14 weeks):
- **Dev A:** product-catalog → session-identity → google-oauth → cart → orders → admin → maintenance
- **Dev B:** event-ingestion → frontend-sdk → ml-recommendations → storefront-ui → deployment-ci

Phase 0 (Day 1) requires co-authoring shared contracts in `app/models/`, `app/config.py`, `app/database.py`, and `app/constants.py`.

## Feature Specifications

Detailed specs live in `openspec/changes/`. Each feature directory contains:
- `proposal.md` — Motivation and scope
- `design.md` — Technical design
- `tasks.md` — Task breakdown with hour estimates
- `specs/` — Individual feature specs with acceptance criteria

## Key Design Decisions

- **Session ID:** Client-generated UUID v4 sent via `X-Session-ID` header on every request.
- **API prefix:** All routes under `/v1/`.
- **Admin auth:** Bearer token (`ATELIER_ADMIN_API_KEY` env var). First Google OAuth user becomes admin.
- **Soft deletes:** All SQLite tables use `deleted_at` column.
- **Event dedup:** `INSERT OR IGNORE` on `event_id` (client-generated UUID) in DuckDB.
- **ML refresh:** Background job every 30 minutes recomputes co-occurrence, popularity, and session sequences.