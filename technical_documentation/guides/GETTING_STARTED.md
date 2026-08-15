# Getting Started — AtelierMarie

Quick 5-minute local setup for new developers.

## Prerequisites

- **Python 3.11+** (run `python3 --version`)
- **Node.js 18+** (run `node --version`)
- **npm** (run `npm --version`)
- **make** (run `make --version`)
- **Git** (run `git --version`)
- **Optional:** `ffmpeg` + `ffprobe` (for video work)
- **Postgres 14+** (for real mode; local dev uses in-memory mock by default)

## Setup (5 minutes)

From repo root:

```bash
# 1. Install dependencies
make setup

# 2. Copy env files
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local

# 3. Start backend (Terminal 1)
make dev-backend
# Backend ready at http://localhost:8000

# 4. Start frontend (Terminal 2)
make dev-frontend
# Frontend ready at http://localhost:3000
```

**Verify it works:**
```bash
curl http://localhost:8000/health
open http://localhost:3000/en
```

## Key Facts

| What | Where | Default |
|------|-------|---------|
| Backend | `http://localhost:8000` | FastAPI, uvicorn, port 8000 |
| Frontend | `http://localhost:3000` | Next.js, hot reload, port 3000 |
| Backend docs | `http://localhost:8000/v1/docs` | Swagger UI (auto-generated) |
| Frontend mock API | `NEXT_PUBLIC_USE_MOCK_API=true` | Default, no backend needed |
| Frontend real API | `NEXT_PUBLIC_API_URL=http://localhost:8000` | Needs running backend |
| Database | `postgresql://atelier:atelier@localhost:5432/atelier_marie` | Postgres (optional for mock mode) |

## Frontend Modes

### Mock Mode (Default, Best for UI)
```bash
# frontend/.env.local
NEXT_PUBLIC_USE_MOCK_API=true
```
- No backend needed
- Fast UI development
- Fake API responses from `frontend/lib/mock-api.ts`

### Real Mode (Integration Testing)
```bash
# frontend/.env.local
NEXT_PUBLIC_USE_MOCK_API=false
NEXT_PUBLIC_API_URL=http://localhost:8000
```
- Backend must be running
- Real Postgres data
- Real auth, cart, checkout, admin

Switch between modes by editing `frontend/.env.local`, then restart frontend dev server.

## Useful Commands

```bash
make help                  # Show all Makefile targets
make setup-backend         # Python venv + pip install
make setup-frontend        # npm install in frontend
make dev-backend           # Start backend (uvicorn --reload)
make dev-frontend          # Start frontend (next dev)
make test                  # Run all tests
make test-backend          # Backend tests only (pytest)
make test-frontend         # Frontend tests only (vitest)
make lint                  # Check code style
make format                # Auto-format code
.venv/bin/python scripts/seed_products.py  # Add sample products
```

## Next Steps

**New developer?**
→ Read `guides/DEVELOPER_WORKFLOWS.md` for common patterns

**Understanding the system?**
→ Read `architecture/SYSTEM_DESIGN.md`

**Need API details?**
→ Check `api/ENDPOINTS.md`

**Stuck?**
→ See `operations/TROUBLESHOOTING.md`

## Troubleshooting

**Port 8000 in use?**
```bash
lsof -i :8000
kill -9 <PID>
```

**Frontend still calls mock API?**
- Set `NEXT_PUBLIC_USE_MOCK_API=false` in `frontend/.env.local`
- Restart: `make dev-frontend`

**No products?**
```bash
.venv/bin/python scripts/seed_products.py
```

**Admin login fails?**
- Set `ADMIN_API_KEY=dev-key` in `.env`
- Restart backend: `make dev-backend`

See `operations/TROUBLESHOOTING.md` for more issues.
