# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AtelierMarie is a luxury candle e-commerce platform for a small family business. The primary goal is selling candles reliably. A secondary goal is learning ML/analytics through an optional sandbox layer.

**Status:** Planning phase complete; implementation not yet started beyond a skeleton FastAPI app in `main.py`.

## Architecture: Two Strict Layers

### Layer 1 — Production E-Commerce (Critical Path)
- Products, cart, checkout, orders, auth, admin
- SQLite only (WAL mode) — never touches DuckDB
- Must work perfectly if Layer 2 is completely OFF
- All responses <200ms

### Layer 2 — Analytics & ML Sandbox (Non-Critical)
- Event collection (async, fire-and-forget)
- DuckDB for analytics storage
- ML recommendations (pre-computed cache, fallback to popular)
- Can crash, be disabled, or be deleted without affecting the store

**Core rule:** Layer 1 code never imports from Layer 2 modules.

See `ARCHITECTURE.md` for full system design and `IMPLEMENTATION_PLAN.md` for the build sequence.

## Technology Stack

- **Backend:** Python 3.11, FastAPI, Pydantic 2, Uvicorn
- **Database:** SQLite (WAL mode) — system of record
- **Auth:** Google OAuth 2.0 + JWT (PyJWT)
- **Frontend:** Next.js 14 (separate app in `frontend/`)
- **Analytics (optional):** DuckDB
- **Hosting:** Oracle Cloud Free Tier (single VPS), Nginx, systemd

## Development Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the backend
uvicorn app.main:app --reload --port 8000

# Run tests
pytest

# Lint
ruff check .
```

## Application Structure

```
app/
├── main.py              # FastAPI app factory + lifespan
├── config.py            # pydantic-settings (env vars)
├── database.py          # SQLite connection management
├── middleware/
│   └── session.py       # Session cookie middleware
├── models/              # Pydantic schemas
├── routes/              # FastAPI routers (thin)
├── services/            # Business logic (testable, no HTTP)
├── analytics/           # Layer 2: event collection + DuckDB (optional)
└── ml/                  # Layer 2: recommendations (experimental)

frontend/                # Next.js app (separate)
deploy/                  # Nginx, systemd, provisioning scripts
```

## Key Design Decisions

- **Anonymous-first:** Full cart/checkout works without login. Session cookie = identity.
- **Prices in cents:** All monetary values stored as integers to avoid float errors.
- **Order snapshots:** `order_items` stores product name + price at purchase time.
- **Order state machine:** pending → confirmed → shipped → delivered. Invalid transitions rejected.
- **Stock validation on cart add:** Tells user immediately if out of stock (not just at checkout).
- **Session rotation on logout:** New session ID issued, old one invalidated. Prevents reuse.
- **Dual admin auth:** JWT (is_admin) for browser, API key for scripts/automation.
- **First-user-is-admin:** First Google OAuth login auto-promoted. No manual DB edits.
- **CSV bulk import:** For initial product catalog load (`POST /v1/admin/products/import`).
- **API prefix:** All routes under `/v1/`.
- **Event collection:** Fire-and-forget JSONL append (O_APPEND, crash-safe, multi-worker safe). Background thread loads into DuckDB every 60s.
- **Recommendations:** Pre-computed cache. Fallback: ML → popularity → featured → random. Never errors.
- **GDPR:** NULL-ification of PII fields (not cascade delete) — preserves order structure.

## Feature Specifications

Lean specs live in `openspec/changes/`:
- `core-ecommerce/` — Products, cart, checkout, orders, auth, admin
- `analytics-sandbox/` — Event collection, DuckDB, admin stats
- `ml-experiments/` — Recommendations (experimental)

Archived v1 (ML-first) specs: `openspec/changes/archive/v1-ml-first/`
