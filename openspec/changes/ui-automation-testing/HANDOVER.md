# Handover — ui-automation-testing (2026-07-26)

Resume with `/opsx:apply ui-automation-testing`. This file has everything the next session needs.

## Status

**16 of 47 tasks done.** Foundation complete: deps, testids codegen, all frontend `data-testid` attributes, CI workflows.

Done: §1.1, §1.5, §2.1–2.4, §3.1–3.10, §5.1 (all marked `[x]` in `tasks.md`).
Remaining: §1.2–1.4, §4, §6, §7, §8 (10 page objects), §9–14 (9 test modules), §15.

## ⚠️ Fix before writing conftest — port is 8000, not 8001

The specs (`proposal.md`, `design.md`, `spec.md`) and `CLAUDE.md:51` and the `test-e2e` Makefile comment all say **:8001**. **This is wrong.** The actual codebase uses **:8000**:

- `frontend/.env.local` → `NEXT_PUBLIC_API_URL=http://localhost:8000`
- `Makefile:83` → `dev-backend` starts `uvicorn ... --port 8000`

**First action next session:** either (a) patch the docs to :8000, or (b) change `dev-backend` to `--port 8001`. Pick one, then the conftest reachability check matches reality. Recommend (a) — the codebase is what ships.

Files to fix if you pick (a):
- `openspec/changes/ui-automation-testing/proposal.md:26`
- `openspec/changes/ui-automation-testing/design.md:5`
- `openspec/changes/ui-automation-testing/specs/ui-e2e-test-suite/spec.md:7`
- `CLAUDE.md:51`
- `Makefile` (the `test-e2e` help comment on the target added this session)

## Refactors made this session (not yet reflected in design.md)

1. **Selenium deps moved out of `pyproject.toml`** → `tests/e2e/requirements.txt`. Design doc still says "Add … to `requirements-dev.txt`" — outdated. Real location is `tests/e2e/requirements.txt`, installed by `make setup-ui-testing`.
2. **`PyJWT` dep dropped** — runtime already has `pyjwt[crypto]>=2.8.0`. The admin-session fixture (§7.1) should `import jwt` from the runtime pyjwt, not a separate PyJWT install.
3. **`Badge.tsx` contract changed** — added `"data-testid"?: string` as an explicit named prop (Badge didn't spread `...props`). Additive, non-breaking. Any future Badge caller can pass `data-testid`.

## What exists on disk

```
Created:
  frontend/lib/testids.ts                  # 14 testid constants (source of truth)
  scripts/generate_testids.py              # regex parser → tests/e2e/testids.py
  tests/e2e/testids.py                     # AUTO-GENERATED, do not hand-edit
  tests/e2e/requirements.txt               # selenium, webdriver-manager, pytest-selenium
  .github/workflows/e2e-pairing.yml        # blocks PRs touching frontend/* without paired test file

Modified:
  pyproject.toml                           # dev extras (no e2e group — moved out)
  Makefile                                 # setup-ui-testing, test-e2e, generate-testids targets
  .github/workflows/frontend-unit-tests.yml # runs `python scripts/generate_testids.py` + git diff --exit-code
  frontend/components/ui/Badge.tsx         # accepts + forwards data-testid
  frontend/components/products/{ProductCard,CategoryFilter,CommentForm,CommentCard}.tsx
  frontend/components/cart/{CartBadge,CartDrawer,CartItem,AddToCartButton}.tsx
  frontend/components/auth/LoginButton.tsx
  frontend/components/orders/OrderStatusBadge.tsx
  frontend/app/[locale]/admin/products/page.tsx
  frontend/app/[locale]/orders/page.tsx
```

## Next task order (recommended)

1. Fix the port (§ above).
2. **§1.2–1.4** — create `tests/e2e/__init__.py`, `tests/e2e/screenshots/.gitkeep`, `conftest.py` (session-scoped headless Chrome, `HEADLESS=0` opt-out, server reachability check on :8000 and :3000, admin-API seed of `e2e-test-candle` product + teardown, `pytest_runtest_makereport` screenshot hook), `pages/__init__.py`, `pages/base_page.py` (`BasePage` with `BASE_URL`, `BASE_LOCALE`, `wait_for()`, `cart` and `header` properties, `assert_url_contains()`).
3. **§4.1** — vitest contract test (`frontend/__tests__/testids.contract.test.tsx`). Cheap early-warning system; catches removed testids before Selenium runs. Renders each of the 10 covered components; asserts `data-testid` present. NOTE: Badge is only reachable via a caller like `OrderStatusBadge` — render `OrderStatusBadge` with a status prop and assert `[data-testid="order-status"]` is present.
4. **§6** — `tests/e2e/components/{header,cart_drawer}.py`.
5. **§7.1** — `inject_admin_session` fixture. Insert a user + session row directly into SQLite (`DB_PATH` env, default `./atelier_marie.db`). Then `driver.get(BASE_URL)` first, then `driver.add_cookie({name:"session_id", value:<uuid>})` AND `driver.add_cookie({name:"atelier_auth", value:<pyjwt-signed token with is_admin=true using JWT_SECRET env>})`. Read `app/config.py` first to confirm the JWT secret env var name — the design says `JWT_SECRET` with default `dev-secret-do-not-use-in-production`; verify before signing.
6. **§8.1–8.10** — 10 page objects. All inherit `BasePage`, all have a URL guard in `__init__` (D16), all navigation methods return the next page object (D13), split success/failure (`submit_expecting_success` / `submit_expecting_error`).
7. **§9–14** — 9 test modules. Use `httpx` for state setup that isn't the subject of the test (D17). Fresh-session-per-test for `test_reactions.py` (D12).
8. **§15.1–15.3** — README section, CLAUDE.md norm on testids, final headless <3min verification.

## Gotchas from the design

- **Locale prefix**: every URL is `/en/...`. `BASE_LOCALE` fixture constant, override for `bg/` runs.
- **Cart hydration race**: `CartContext` hydrates in `useEffect` after mount. After ANY navigation, page objects MUST `wait_for(cart-badge)` before reading `item_count`. Never assume it's there immediately.
- **`AddToCartButton` success state is 1500ms** (see `AddToCartButton.tsx:40`). Add-to-cart tests wait for success state before asserting badge count.
- **Reaction rate limit**: fresh WebDriver / `driver.delete_all_cookies()` between reaction tests. Not doing this = flaky 429s.
- **Seed product `e2e-test-candle`**: must be `is_active=1` (public product routes filter this). Assert `GET /en/products/e2e-test-candle` returns 200 in conftest before yielding to tests.
- **Admin needs BOTH cookies**: `session_id` alone leaves `AuthContext.isAdmin === false`, admin pages redirect. Set `atelier_auth` JWT too.

## How to run once conftest is written

```
make setup-ui-testing                       # one-time; installs Selenium into .venv
make dev-backend                            # terminal 1
make dev-frontend                           # terminal 2
make test-e2e                               # terminal 3
HEADLESS=0 make test-e2e                    # headed debug
.venv/bin/pytest tests/e2e/test_cart.py -v  # single file
```

Screenshots on failure land in `tests/e2e/screenshots/{test_name}.png`.

## Change dir

`openspec/changes/ui-automation-testing/` — proposal.md, design.md, tasks.md, specs/ui-e2e-test-suite/spec.md. All complete; `openspec status --change ui-automation-testing` reports `isComplete: true`.
