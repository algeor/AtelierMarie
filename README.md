# Atelier Marie

Luxury handcrafted candle e-commerce platform.

## Prerequisites

- **Node.js** 18+ (tested with 24.x)
- **Python** 3.11+
- **npm** (comes with Node.js)

## Project Structure

```
├── app/              # Python backend (FastAPI)
├── frontend/         # Next.js 14 frontend
├── deploy/           # Nginx, systemd, provisioning
└── openspec/         # Feature specifications
```

## Quick Start

### Frontend (Next.js)

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

The frontend runs at [http://localhost:3000](http://localhost:3000).

By default, `NEXT_PUBLIC_USE_MOCK_API=true` — the app uses mock data and **does not require the backend** to be running.

### Backend (FastAPI)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API runs at [http://localhost:8000](http://localhost:8000).

## Environment Variables

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |
| `NEXT_PUBLIC_USE_MOCK_API` | `true` | Use mock data (no backend needed) |

### Backend

Configured via `app/config.py` (pydantic-settings). Copy `.env.example` if available.

## Development Commands

### Frontend

```bash
cd frontend
npm run dev        # Start dev server (port 3000)
npm run build      # Production build
npm run lint       # ESLint
```

### Backend

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000   # Dev server
pytest                                       # Run tests
pytest --cov=app --cov-report=term-missing   # Tests + coverage
ruff check .                                 # Lint
ruff format .                                # Format
```

## Running Frontend Without Backend

The frontend is fully functional with mock data:

1. Ensure `NEXT_PUBLIC_USE_MOCK_API=true` in `frontend/.env.local`
2. Run `npm run dev` from the `frontend/` directory
3. Browse to http://localhost:3000

Mock data provides 4 sample products across categories (Floral, Woody, Fresh, Gourmand).

## Connecting Frontend to Backend

1. Start the backend: `uvicorn app.main:app --reload --port 8000`
2. Set `NEXT_PUBLIC_USE_MOCK_API=false` in `frontend/.env.local`
3. Restart the frontend dev server
4. The frontend now fetches from the real API at `NEXT_PUBLIC_API_URL`

## Testing

### Backend & Frontend Unit Tests

```bash
make test               # Run backend (pytest) + frontend (vitest)
make test-backend       # pytest only
make test-frontend      # vitest only
```

### End-to-End Tests (Selenium)

E2E tests exercise the running frontend against the running backend via headless Chrome. Dependencies are opt-in (kept out of the runtime install).

**One-time setup:**

```bash
make setup-ui-testing   # Installs selenium + webdriver-manager + pytest-selenium into .venv
```

**Run the suite** (requires both dev servers already running):

```bash
# Terminal 1
make dev-backend        # FastAPI on :8000

# Terminal 2
make dev-frontend       # Next.js on :3000 (must be configured to hit the real API — NEXT_PUBLIC_USE_MOCK_API=false)

# Terminal 3
make test-e2e           # Runs tests/e2e/ against the live servers
```

Set `HEADLESS=0` to watch the browser drive the tests:

```bash
HEADLESS=0 make test-e2e
```

Failing tests drop a screenshot into `tests/e2e/screenshots/{test_name}.png`.

The suite reads `.env` automatically for `JWT_SECRET` and `ADMIN_API_KEY` — both must match the backend for admin-session tests to authenticate. Externally-set env vars take precedence, so CI can still override.

`make test-e2e` runs with `pytest -n 4 --dist worksteal` (four parallel Chrome sessions). Full suite is ~2:30 wall-clock; sequential (`-n0`) is ~6:20. Use `-n0` when debugging a single test to keep output linear.

### Testid Codegen

E2E locators live in a single source of truth (`frontend/lib/testids.ts`). The Python-side mirror is generated:

```bash
make generate-testids   # Regenerates tests/e2e/testids.py from testids.ts
```

CI enforces that `testids.py` is not stale — any rename in `testids.ts` must be committed alongside a regenerated `testids.py`.
