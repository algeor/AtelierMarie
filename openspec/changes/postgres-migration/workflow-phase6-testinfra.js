// =============================================================================
// Postgres Migration — §6 Test Infrastructure port  (WITH REVIEW GATES)
// =============================================================================
// LAUNCH:  Workflow({ scriptPath: "<this file>" })   (ultracode already opted in)
//
// WHY THIS RUNS BEFORE §4/§5:
//   The design's per-domain green-test gate (Migration Plan step 5, Phase 2)
//   cannot run until the test fixtures speak Postgres. §6 ports conftest/fixtures
//   to the template-clone model (design Decision 15) so every later §4 domain
//   slice can be taken to green.
//
// REVIEW MODEL (same as Phase-1 workflow):
//   Each editing step is followed by an adversarial reviewer (general-purpose
//   agent — 'code-reviewer' is NOT available in this env) that inspects the REAL
//   on-disk diff and returns pass/blockers. On fail it THROWS → chain halts.
//
// CACHE NOTE (learned in Phase-1): resumeFromRunId caches on the agent call
//   (prompt+opts), NOT on disk. If a gate fails, fix the files AND edit the
//   failing editor step's prompt (to force a cache miss) before resuming.
//
// PREREQUISITES:
//   - local Postgres up (compose.yml) + `alembic upgrade head` applied.
//   - Phase-1 + §3 connection layer already landed (get_db() is psycopg).
//
// KNOWN REALITY (discovered during scoping — feed to agents so they don't
//   assume the design's idealized layout):
//   - The canonical central conftest IS the repo-ROOT /conftest.py (git-tracked,
//     ~12.6KB, all SQLite: sqlite3.connect, PRAGMA foreign_keys, "?", init_db(path),
//     datetime('now')). pytest rootdir = repo root, so it ALWAYS loads even though
//     testpaths=["tests"]. It defines the shared fixtures (db, app, client,
//     service_db, db_path, make_session, seed_products) AND the ADMIN_API_KEY
//     constant. tests/test_auth.py does `from conftest import ADMIN_API_KEY`
//     (top-level module import → resolves to root /conftest.py).
//   - PITFALL FROM THE FAILED RUN: an earlier attempt created a DUPLICATE
//     tests/conftest.py with good psycopg code but LEFT the broken SQLite root
//     /conftest.py in place. pytest loaded BOTH (root wins for same-named
//     fixtures), so the port never took effect and same-named fixtures collided
//     across two levels. The port MUST edit the root /conftest.py IN PLACE and
//     DELETE the duplicate tests/conftest.py — consolidate everything (fixtures,
//     make_session/seed_products, ADMIN_API_KEY) into the single root file.
//   - tests/realapp/conftest.py IS central for the realapp suite: it uses
//     DATABASE_PATH env + init_db(db_path) (SQLite) with function-scoped fresh
//     DB per test and a no-op _clean_tables. init_db() is now psycopg and takes
//     a URL, so this conftest is already broken against the new layer.
// =============================================================================

export const meta = {
  name: 'pg-migration-phase6-testinfra-reviewed',
  description: '§6 test-infra port to Postgres template-clone (Decision 15): discover scattered fixtures → author central conftest + worker-DB clone + TRUNCATE cleanup → port helpers (make_session/seed_products) → review → boot the suite collection → report green/red baseline',
  phases: [
    { title: 'Discover' },
    { title: 'ConftestCore' },
    { title: 'ReviewConftest' },
    { title: 'PortHelpers' },
    { title: 'ReviewHelpers' },
    { title: 'CollectSmoke' },
  ],
}

const DISCOVER_SCHEMA = {
  type: 'object',
  properties: {
    scatteredFixtures: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          fixture: { type: 'string' }, // db | app | service_db | client | db_path | ...
          scope: { type: 'string' },
          sqliteisms: { type: 'string' }, // what SQLite-specific behavior it relies on
        },
        required: ['file', 'fixture'],
      },
    },
    helperDefs: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          name: { type: 'string' }, // make_session | seed_products
          signature: { type: 'string' },
        },
        required: ['file', 'name'],
      },
    },
    sqliteOnlyTests: {
      type: 'array',
      items: { type: 'string' }, // files asserting PRAGMA/WAL/FTS shadow/sqlite_master/file paths (§6.4)
    },
    plan: { type: 'string' }, // concrete plan: what conftest(s) to create/edit, curated TRUNCATE allowlist source, scope flips
  },
  required: ['scatteredFixtures', 'helperDefs', 'plan'],
}

const DIFF_SCHEMA = {
  type: 'object',
  properties: {
    filesChanged: { type: 'integer' },
    summary: { type: 'string' },
    risks: { type: 'array', items: { type: 'string' } },
  },
  required: ['filesChanged', 'summary'],
}

const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    pass: { type: 'boolean' },
    blockers: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['pass', 'blockers'],
}

const COLLECT_SCHEMA = {
  type: 'object',
  properties: {
    collectsClean: { type: 'boolean' }, // pytest --collect-only succeeds (no import/fixture errors)
    collectionErrors: { type: 'array', items: { type: 'string' } },
    sampleRunPasses: { type: 'boolean' }, // a tiny targeted subset (e.g. one service test) went green
    details: { type: 'string' },
    blockers: { type: 'array', items: { type: 'string' } },
  },
  required: ['collectsClean', 'details'],
}

async function reviewGate(stepName, phaseTitle, charge) {
  const verdict = await agent(
    `Adversarially review the "${stepName}" step's edits. Inspect the ACTUAL diff ` +
    `on disk (git diff of the working tree). Default to pass=false if uncertain. ` +
    `${charge} Return pass + blockers (blockers MUST be [] when pass=true).`,
    { phase: phaseTitle, schema: REVIEW_SCHEMA, agentType: 'general-purpose', effort: 'high' },
  )
  if (!verdict || !verdict.pass) {
    const bl = verdict ? verdict.blockers.join('; ') : 'reviewer returned null'
    throw new Error(`Review gate FAILED for ${stepName}: ${bl}`)
  }
  return verdict
}

// --- Step 1: Discover the real fixture/helper landscape (READ ONLY) ---------
phase('Discover')
const discover = await agent(
  `Read-only discovery for the §6 Postgres test-infra port. The canonical central ` +
  `conftest is the repo-ROOT /conftest.py (git-tracked, SQLite) — it defines the ` +
  `shared db / app / client / service_db / db_path fixtures, make_session, ` +
  `seed_products, and ADMIN_API_KEY. pytest rootdir = repo root so it always loads. ` +
  `NOTE: a prior failed run created a DUPLICATE tests/conftest.py (good psycopg ` +
  `code) while leaving the SQLite root conftest in place — flag BOTH files and ` +
  `note the same-named fixture collision; the port will consolidate into root and ` +
  `delete the duplicate. Map the reality: ` +
  `(1) every definition of the db / service_db / app / client / db_path fixtures ` +
  `across /conftest.py, tests/conftest.py, and tests/realapp/conftest.py, with ` +
  `scope and the SQLite-specific behavior ` +
  `each relies on (init_db(path), sqlite3.Row, PRAGMA foreign_keys, :memory:, ` +
  `DATABASE_PATH); (2) every def of make_session and seed_products and their ` +
  `signatures (root versions take sqlite3.Connection + use "?" and datetime('now')); ` +
  `(3) tests that assert SQLite internals (PRAGMA/WAL/FTS shadow tables/` +
  `sqlite_master/old SQLite migrations/file paths) — these are §6.4 rewrite/remove ` +
  `candidates; also flag every "from conftest import ..." so consolidation doesn't ` +
  `break imports. Then produce a concrete PLAN for Decision 15: confirm the target ` +
  `is the ROOT /conftest.py edited IN PLACE with tests/conftest.py DELETED, the ` +
  `session-scoped template-migrate + per-worker ` +
  `CREATE DATABASE ... TEMPLATE mechanics, the CURATED volatile-table TRUNCATE ` +
  `allowlist (name its source — the initial migration's table list), and which ` +
  `module→session scope flips are needed. Do NOT edit anything.`,
  { phase: 'Discover', schema: DISCOVER_SCHEMA },
)

// --- Step 2: Author the central conftest + clone/truncate model + review ----
phase('ConftestCore')
const conftest = await agent(
  `Implement design Decision 15 test provisioning from this discovery: ` +
  `${JSON.stringify(discover).slice(0, 6000)}. ` +
  `TARGET FILE — CRITICAL: the canonical central conftest is the repo-ROOT ` +
  `/conftest.py (git-tracked, currently SQLite). Edit that file IN PLACE and ` +
  `DELETE the duplicate tests/conftest.py (git rm / delete it), consolidating ` +
  `EVERYTHING — the db/app/client/service_db/db_path fixtures, make_session, ` +
  `seed_products, and the ADMIN_API_KEY constant — into the single root ` +
  `/conftest.py. Do NOT leave two same-named conftests: the failed run's bug was a ` +
  `duplicate tests/conftest.py colliding with the root one (root wins, so the port ` +
  `silently had no effect). Preserve the ROOT file's existing ADMIN_API_KEY VALUE ` +
  `so \`from conftest import ADMIN_API_KEY\` in tests/test_auth.py keeps resolving to ` +
  `the same string (and keep setting the ADMIN_API_KEY env var to that same value). ` +
  `Concretely: ` +
  `(a) session-scoped setup migrates ONE template database once via ` +
  `\`alembic upgrade head\` against the reachable Postgres (DATABASE_URL); ` +
  `(b) each xdist worker does CREATE DATABASE <worker_db> TEMPLATE <template>, ` +
  `worker name from PYTEST_XDIST_WORKER (single-DB fallback when xdist off); ` +
  `(c) flip db_path/app/db/service_db fixtures module→session scope so the ` +
  `worker DB is created once per worker; (d) _clean_tables (autouse, per test) ` +
  `runs TRUNCATE <curated volatile tables> RESTART IDENTITY CASCADE — a curated ` +
  `ALLOWLIST of volatile/data tables, NOT all tables; deliberately EXCLUDE ` +
  `migration-seed tables (taxonomy, faq_items, terms/privacy/cookies pages, ` +
  `site_banners, delivery/econt/inventory settings, about content) so seeded rows ` +
  `persist via the clone; (e) retire the _seed_site_banner/_seed_delivery_settings/` +
  `_seed_inventory_settings re-seed calls; (f) insert the FakeSessionMiddleware ` +
  `fake-session row via psycopg after clone; ` +
  `(f2) CRITICAL — the app fixture MUST rebuild the ASGI middleware stack to ` +
  `install a FakeSessionMiddleware resolving cookieless requests to the seeded ` +
  `FAKE_SESSION_ID ("test-session"), NOT the real SessionMiddleware minting a ` +
  `fresh UUID4. There is NO existing "class FakeSessionMiddleware" in tree or git ` +
  `history — DEFINE it (minimal ASGI middleware setting the fake session id) and ` +
  `swap it in for SessionMiddleware on the app fixture (edit app.user_middleware + ` +
  `app.build_middleware_stack()). Without it the seeded row is orphaned and route ` +
  `tests break. (The deleted duplicate tests/conftest.py already contained a ` +
  `working FakeSessionMiddleware + swap + clone/truncate implementation — reuse ` +
  `that logic when consolidating into root, do not reinvent it.) ` +
  `(f3) REAL-MIDDLEWARE FILES — tests/test_auth_integration.py deliberately uses ` +
  `the REAL SessionMiddleware (it is the tests/realapp pattern living under tests/). ` +
  `You MUST fully port its module-scoped db_path/app fixtures, do NOT half-edit and ` +
  `do NOT leave them on SQLite init_db(<path>). Mirror the ALREADY-PORTED ` +
  `tests/realapp/conftest.py app fixture: override the root app by consuming the ` +
  `root's session-scoped \`worker_database_url\`, set os.environ["DATABASE_URL"] to ` +
  `it, call init_db(worker_database_url) (URL, never a .db path), build create_app() ` +
  `with the REAL SessionMiddleware (NO FakeSessionMiddleware swap), and keep its ` +
  `extra Google/CORS/ADMIN_API_KEY env setup. DELETE its local module-scoped ` +
  `db_path fixture (the file's tests take db_path only for ordering; they inherit ` +
  `the root's db_path shim which returns worker_database_url) — leaving a local ` +
  `db_path/app shadows the root session-scoped fixtures and reintroduces the exact ` +
  `SQLite-init_db collision this consolidation removes. Its former sqlite3 _clean ` +
  `loop stays removed (root autouse _clean_tables covers it). Verify no init_db(` +
  `<sqlite path>) and no setenv("DATABASE_PATH", ...) survive in that file. ` +
  `(g) fix tests/realapp/conftest.py ` +
  `(currently init_db(db_path) SQLite) to the same model. Any per-test-file db/app ` +
  `fixture that shadowed the central ones should now consume the root conftest. ` +
  `Keep get_db() as the single chokepoint (do NOT change service signatures). ` +
  `Do NOT commit. Report a diff summary (include that tests/conftest.py was deleted).`,
  { phase: 'ConftestCore', schema: DIFF_SCHEMA },
)
await reviewGate('ConftestCore', 'ReviewConftest',
  `FIRST confirm the consolidation: the ROOT /conftest.py is the single central ` +
  `conftest and now holds the psycopg fixtures + make_session/seed_products + ` +
  `ADMIN_API_KEY; the duplicate tests/conftest.py has been DELETED (git status ` +
  `shows it removed, not still present); there are NOT two same-named conftests ` +
  `with colliding fixtures; \`from conftest import ADMIN_API_KEY\` still resolves ` +
  `(root value preserved). Then confirm against Decision 15: ` +
  `template DB is migrated ONCE (not per worker); ` +
  `each worker clones via CREATE DATABASE ... TEMPLATE; fixtures are SESSION-scoped ` +
  `(not module); _clean_tables TRUNCATEs a CURATED volatile allowlist with RESTART ` +
  `IDENTITY CASCADE and does NOT truncate migration-seed tables; no _seed_* re-seed ` +
  `calls remain for tables the clone already carries; the fake-session row is ` +
  `inserted via psycopg; FakeSessionMiddleware is defined and swapped in on the app ` +
  `fixture; realapp conftest no longer calls init_db(path) with a ` +
  `SQLite path. Also confirm tests/test_auth_integration.py is FULLY ported (not ` +
  `half-edited): it has NO local module-scoped db_path fixture and NO init_db(<.db ` +
  `path>)/setenv("DATABASE_PATH") — its app fixture consumes worker_database_url, ` +
  `calls init_db(url), and keeps the REAL SessionMiddleware (no fake swap), ` +
  `mirroring tests/realapp/conftest.py; it does not shadow the root session-scoped ` +
  `fixtures. Re-grep the repo-root /conftest.py for any remaining sqlite3.connect, ` +
  `:memory:, PRAGMA, init_db(<path>), DATABASE_PATH, or "?" placeholders, and ` +
  `confirm tests/conftest.py no longer exists on disk.`)

// --- Step 3: Port make_session / seed_products helpers + review -------------
phase('PortHelpers')
const helpers = await agent(
  `Port the test helpers to psycopg (Task 6.3). By this point the ConftestCore step ` +
  `has consolidated everything into the repo-ROOT /conftest.py and DELETED the ` +
  `duplicate tests/conftest.py — so make_session and seed_products now live in the ` +
  `root /conftest.py. Discovery found these original defs: ` +
  `${JSON.stringify(discover.helperDefs)}. Verify make_session and seed_products in ` +
  `the root /conftest.py are fully ported: "?"→"%s", datetime('now')→` +
  `CURRENT_TIMESTAMP, take a pooled dict_row ` +
  `connection (NOT sqlite3.Connection), drop PRAGMA foreign_keys (always on in ` +
  `Postgres), and update type hints. Confirm service_db is a pooled connection ` +
  `against the same worker DB, not its own SQLite file. Do NOT recreate a shared ` +
  `tests/helpers module and do NOT recreate tests/conftest.py — the single source ` +
  `is the root /conftest.py. Fix any test file still doing "from tests.conftest ` +
  `import ..." or importing these helpers from the deleted duplicate so imports ` +
  `resolve to the root conftest. If any helper still carries SQLite-isms, finish ` +
  `the port here. Do NOT commit. Report a diff summary.`,
  { phase: 'PortHelpers', schema: DIFF_SCHEMA },
)
await reviewGate('PortHelpers', 'ReviewHelpers',
  `Confirm make_session and seed_products live ONLY in the root /conftest.py (no ` +
  `duplicate tests/conftest.py, no stray shared helpers module) and each takes a ` +
  `psycopg/dict_row connection ` +
  `(no sqlite3.Connection type hint remains); all "?" became "%s" and ` +
  `datetime('now') became CURRENT_TIMESTAMP inside them; no PRAGMA foreign_keys ` +
  `call survives; every "from conftest"/"from tests.conftest" import across tests/ ` +
  `resolves to the root file. Re-grep the ` +
  `helper defs for stray "?" placeholders and sqlite3 references.`)

// --- Step 4: Collection smoke (READ ONLY assessment) ------------------------
phase('CollectSmoke')
const collect = await agent(
  `Assess the ported test infra against the live local Postgres (compose.yml up, ` +
  `alembic at head). Run \`.venv/bin/pytest tests/ --collect-only -q\` and confirm ` +
  `collection succeeds with no import/fixture errors (this proves the conftest and ` +
  `helper ports are syntactically and structurally sound). Then run ONE small ` +
  `money-path service test file (e.g. a cart or product service test) with ` +
  `\`-p no:xdist\` to exercise the single-DB fallback + TRUNCATE cleanup end to end, ` +
  `and report whether it passes. Do NOT fix code — this is assessment. Note that ` +
  `most DOMAIN tests are NOT expected green yet: §4 SQL porting per domain comes ` +
  `after this. In scope here: clean collection + the fixture/clone/truncate ` +
  `machinery working, proven by at least one green test. Report collectsClean, ` +
  `sampleRunPasses, collectionErrors, blockers.`,
  { phase: 'CollectSmoke', schema: COLLECT_SCHEMA },
)

return {
  discover: { fixtures: discover.scatteredFixtures.length, helpers: discover.helperDefs.length, sqliteOnlyTests: discover.sqliteOnlyTests, plan: discover.plan },
  conftest,
  helpers,
  collect,
  reviewModel: 'ConftestCore and PortHelpers each passed an adversarial review gate (chain halts on fail).',
  humanGate: 'Review the conftest + helper diffs and the collection smoke result before committing. Nothing committed. §4 per-domain SQL porting (money path first) is the next workflow and can now use a real green-test gate.',
}
