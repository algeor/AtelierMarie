# Atelier Marie Technical Documentation

Start here.

These docs are for mid-level devs who need to change the project without reading every OpenSpec archive file first.

## Fast Path

- Need orientation: [00-project-map.md](00-project-map.md)
- Need exact file map: [FILE_MAP.md](FILE_MAP.md)
- Need code lookup: [reference/code-index.md](reference/code-index.md)
- Need test lookup: [reference/test-map.md](reference/test-map.md)
- Need archived spec coverage: [reference/archive-coverage-map.md](reference/archive-coverage-map.md)
- Need crop/editor/lightbox guidance: [domains/13-product-media-editor-and-lightbox.md](domains/13-product-media-editor-and-lightbox.md)
- Need term meanings: [reference/glossary.md](reference/glossary.md)

## Pick Your Lane

| If you are changing... | Read these first |
|---|---|
| App startup, DB, layers, flows | `architecture/` |
| FastAPI routes/services/models | `backend/` |
| Next.js pages/components/state | `frontend/` |
| A concrete feature | `domains/` |
| How to safely make/release/debug a change | `operations/` |
| Quick older summaries | `features/` |

## The Rule That Matters Most

Layer 1 sells candles.

It must work when analytics is off, DuckDB is gone, Stripe is unavailable, email is slow, or a courier API is down.

Do not make checkout depend on optional systems.

## Suggested Reading Order For New Devs

1. [00-project-map.md](00-project-map.md)
2. [architecture/03-request-and-data-flow.md](architecture/03-request-and-data-flow.md)
3. [backend/01-routes-services-models.md](backend/01-routes-services-models.md)
4. [frontend/02-state-api-data.md](frontend/02-state-api-data.md)
5. The domain doc for the thing you are touching.
6. [operations/01-change-playbooks.md](operations/01-change-playbooks.md)

## What These Docs Are Based On

Primary source:

- `openspec/changes/archive`

Also checked to avoid stale guidance:

- current app code under `app/`
- current frontend code under `frontend/`
- active payment/GDPR OpenSpec notes where current code has live behavior not fully represented by archived specs
- existing `docs/ARCHITECTURE.md` and `docs/DATABASE_SCHEMA.md`
