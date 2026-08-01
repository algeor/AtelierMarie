.PHONY: help setup setup-backend setup-frontend test test-backend test-unit test-integration \
       test-frontend test-chrome-stack lint lint-backend lint-frontend typecheck format clean dev \
       stripe-webhook-secret dev-stripe-webhook

# Default
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}'

# ─── Setup ────────────────────────────────────────────────────────────────────

setup: setup-backend setup-frontend ## Install all dependencies (backend + frontend)

setup-backend: ## Create venv and install Python deps (including dev)
	@echo "═══ Setting up Python backend ═══"
	@if [ ! -d .venv ]; then python3.11 -m venv .venv; fi
	.venv/bin/pip install --quiet --upgrade pip
	.venv/bin/pip install --quiet -e ".[dev]"
	@echo "✓ Backend ready (.venv activated)"
	@echo "Stripe webhooks: run 'make stripe-webhook-secret', set STRIPE_WEBHOOK_SECRET, then 'make dev-stripe-webhook'"

setup-frontend: ## Install Node.js dependencies
	@echo "═══ Setting up Next.js frontend ═══"
	cd frontend && npm install --silent
	@echo "✓ Frontend ready"

# ─── Test ─────────────────────────────────────────────────────────────────────

test: test-backend test-frontend ## Run ALL tests (backend + frontend)

test-backend: ## Run pytest (Python backend)
	@echo "═══ Running backend tests (pytest) ═══"
	.venv/bin/pytest tests/ -v --tb=short

test-unit: ## Run only unit tests (fast — excludes integration)
	@echo "═══ Running unit tests ═══"
	.venv/bin/pytest tests/ -v --tb=short -m "not integration"

test-integration: ## Run only integration tests (real middleware)
	@echo "═══ Running integration tests ═══"
	.venv/bin/pytest tests/realapp/ -v --tb=short -m integration

test-frontend: ## Run vitest (Next.js frontend)
	@echo "═══ Running frontend tests (vitest) ═══"
	cd frontend && npx vitest run

test-chrome-stack: ## Run full-stack Chrome smoke tests (backend + frontend + fake Speedy)
	@echo "═══ Running Chrome full-stack smoke tests ═══"
	cd frontend && npm run test:chrome:stack

test-backend-cov: ## Run pytest with coverage report
	@echo "═══ Running backend tests with coverage ═══"
	.venv/bin/pytest tests/ --cov=app --cov-report=term-missing --tb=short

test-frontend-watch: ## Run vitest in watch mode
	cd frontend && npx vitest

# ─── Lint & Format ───────────────────────────────────────────────────────────

lint: lint-backend lint-frontend ## Lint everything

lint-backend: ## Lint Python with ruff
	@echo "═══ Linting backend (ruff) ═══"
	.venv/bin/ruff check .

lint-frontend: ## Lint frontend with ESLint
	@echo "═══ Linting frontend (eslint) ═══"
	cd frontend && npx next lint

typecheck: ## Type-check Python with mypy
	@echo "═══ Type-checking backend (mypy) ═══"
	.venv/bin/mypy

format: ## Auto-format Python code with ruff
	.venv/bin/ruff format .
	.venv/bin/ruff check --fix .

# ─── Dev Servers ──────────────────────────────────────────────────────────────

dev: ## Start both backend and frontend (requires two terminals — use dev-backend / dev-frontend)
	@echo "Use 'make dev-backend' and 'make dev-frontend' in separate terminals"
	@echo "Or: make dev-backend & make dev-frontend"

dev-backend: ## Start FastAPI dev server (port 8000)
	.venv/bin/uvicorn app.main:app --reload --reload-dir app --port 8000

dev-frontend: ## Start Next.js dev server (port 3000)
	npm run dev

stripe-webhook-secret: ## Print local Stripe webhook secret for STRIPE_WEBHOOK_SECRET
	.venv/bin/python scripts/stripe_webhook_forward.py secret

dev-stripe-webhook: ## Forward Stripe CLI webhooks to the local backend
	.venv/bin/python scripts/stripe_webhook_forward.py listen



# ─── Clean ────────────────────────────────────────────────────────────────────

clean: ## Remove build artifacts, caches, venv
	rm -rf .venv
	rm -rf frontend/node_modules frontend/.next frontend/.next-dev frontend/.next-build
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleaned"
