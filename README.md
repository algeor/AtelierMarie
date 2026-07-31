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
├── deploy/           # Nginx, systemd, provisioning, Docker deployment guide
├── openspec/         # Feature specifications
├── compose.yml       # Docker Compose stack (backend + frontend)
└── Dockerfile.backend
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

### With Docker (backend + frontend)

Run both services as containers with Docker Compose. Nginx stays on the host as the only public listener; runtime data lives in Docker volumes.

```bash
# 1. Create the env file and fill in real values
cp .env.docker.example .env.docker
chmod 600 .env.docker
#    Set at least: JWT_SECRET, ADMIN_API_KEY, FRONTEND_URL, CORS_ORIGINS,
#    NEXT_PUBLIC_API_URL, NEXT_PUBLIC_MEDIA_URL, NEXT_PUBLIC_SITE_URL
#    (generate secrets with: openssl rand -base64 48)

# 2. Build and start (detached)
docker compose --env-file .env.docker up -d --build

# 3. Verify
docker compose ps
curl http://127.0.0.1:8001/health   # backend
curl -I http://127.0.0.1:3000       # frontend

# Logs / update / stop
docker compose logs -f
docker compose --env-file .env.docker up -d --build   # pull + rebuild after `git pull`
docker compose down
```

The backend listens on `127.0.0.1:8001` and the frontend on `127.0.0.1:3000`. Frontend `NEXT_PUBLIC_*` values are baked in at build time, so re-run the build step after changing them.

See [`deploy/docker-deployment.md`](deploy/docker-deployment.md) for the full VPS deployment guide (host Nginx config, persistent volumes, backups, and updates).

## Environment Variables

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |
| `NEXT_PUBLIC_MEDIA_URL` | API URL, or relative `/static` in mock mode | Public origin for product media served from `/static/*` |
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

Mock data provides 4 sample products across categories (Floral, Woody, Fresh, Gourmand). Product media is served from bundled files in `frontend/public/static/products` unless `NEXT_PUBLIC_MEDIA_URL` is set.

## Connecting Frontend to Backend

1. Start the backend: `uvicorn app.main:app --reload --port 8000`
2. Set `NEXT_PUBLIC_USE_MOCK_API=false` in `frontend/.env.local`
3. Restart the frontend dev server
4. The frontend now fetches from the real API at `NEXT_PUBLIC_API_URL`
5. Set `NEXT_PUBLIC_MEDIA_URL` when product media is served from a separate static host or CDN; otherwise `/static/*` media falls back to `NEXT_PUBLIC_API_URL`
