// =============================================================================
// Postgres Migration — §4 Per-domain SQL port: MONEY PATH FIRST  (REVIEW GATES)
// =============================================================================
// LAUNCH:  Workflow({ scriptPath: "<this file>" })   (ultracode already opted in)
//
// WHY MONEY PATH FIRST:
//   Cart → checkout → order is the critical revenue path (CLAUDE.md Layer 1).
//   §3 landed the blind ?->%s codemod + psycopg get_db(), but DELIBERATELY
//   deferred per-domain transactional SQL: 32 `BEGIN IMMEDIATE`, 12 Role-2
//   datetime('now', interval) sites, INSERT OR IGNORE, lastrowid, sqlite3
//   exception handlers, and sqlite3.Connection/Row type hints. This slice ports
//   ONLY the money-path domain (cart/order/product services + orders route) and
//   takes it to green — proving the pattern before the broader §4 sweep.
//
// GREEN GATE (now possible — §6 test-infra is committed, bb11afb):
//   test_pricing.py already green. This slice must additionally take
//   test_cart_routes.py + test_order_routes.py (+ their service tests) green.
//   Current known failure: `syntax error at or near "IMMEDIATE"` (BEGIN IMMEDIATE
//   in cart_service). That is the canonical symptom to clear.
//
// KNOWN SQLite->Postgres TRANSFORMS for this domain (feed to agents):
//   - `BEGIN IMMEDIATE` -> `BEGIN` (psycopg/PG has no IMMEDIATE; get_db() already
//     manages the transaction — many BEGINs may be redundant under the pool's
//     autocommit=off. Prefer removing the manual BEGIN and relying on get_db()'s
//     commit/rollback, OR use explicit `with conn.transaction():` for nested
//     savepoint semantics. Do NOT emit bare `BEGIN IMMEDIATE`.)
//   - Role-2 datetime: `datetime('now', '-7 days')` -> `CURRENT_TIMESTAMP - INTERVAL '7 days'`
//     (and `+` variants). These are the 12 sites §3 left; money-path ones only here.
//   - `INSERT ... ON CONFLICT ... DO NOTHING` replaces `INSERT OR IGNORE`.
//   - `cursor.lastrowid` -> `INSERT ... RETURNING id` (use insert_returning_id()
//     helper from app.database if present) — but money-path IDs are text SKUs /
//     UUIDs, so lastrowid is unlikely here; flag if found.
//   - `sqlite3.IntegrityError` -> `psycopg.errors.UniqueViolation` /
//     `psycopg.errors.CheckViolation` (or the `IntegrityError` alias exported by
//     app.database); `sqlite3.Error` -> `psycopg.Error`. The `CHECK (stock >= 0)`
//     violation must still map to InsufficientStock semantics.
//   - `sqlite3.Connection` / `sqlite3.Row` type hints -> `psycopg.Connection`
//     (rows are dict_row mappings — keyed access already works).
//   - Native datetime: psycopg adapts python datetime to timestamptz directly;
//     drop any strftime(SQLITE_DATETIME_FORMAT) round-trips.
//
// SCOPE (money path ONLY — do NOT touch other domains this slice):
//   app/services/cart_service.py, app/services/order_service.py,
//   app/services/product_service.py, app/routes/orders.py, app/routes/cart.py
//   (+ app/middleware/session.py:44 strptime-on-native-datetime bug IF it blocks
//   the money-path tests — it surfaced in test_auth_integration; fix only if in
//   the way of THIS slice's green gate, else leave for the auth slice).
//
// REVIEW MODEL: each editing step -> adversarial general-purpose reviewer over
//   the real on-disk diff (NOT 'code-reviewer' — absent in this env). Throws on
//   fail -> chain halts. Cache: resumeFromRunId keys on prompt+opts; to force a
//   re-run after a manual fix, edit that step's prompt.
// =============================================================================

export const meta = {
  name: 'pg-migration-phase4-moneypath-reviewed',
  description: '§4 money-path SQL port (cart/order/product services + orders/cart routes): discover domain SQLisms → port BEGIN IMMEDIATE/Role-2 datetime/INSERT OR IGNORE/sqlite3 exceptions+hints → review gate → green-test gate (cart+order+pricing)',
  phases: [
    { title: 'Discover' },
    { title: 'PortMoneyPath' },
    { title: 'ReviewPort' },
    { title: 'GreenGate' },
  ],
}

const DISCOVER_SCHEMA = {
  type: 'object',
  properties: {
    sites: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          line: { type: 'integer' },
          kind: { type: 'string' }, // begin_immediate | role2_datetime | insert_or_ignore | lastrowid | sqlite_exception | type_hint | strftime
          snippet: { type: 'string' },
          transform: { type: 'string' }, // the specific PG rewrite for this site
        },
        required: ['file', 'kind'],
      },
    },
    txnNotes: { type: 'string' }, // how BEGIN IMMEDIATE interacts with get_db()'s pool txn mgmt in this domain
    plan: { type: 'string' },
  },
  required: ['sites', 'plan'],
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

const GATE_SCHEMA = {
  type: 'object',
  properties: {
    cartGreen: { type: 'boolean' },
    orderGreen: { type: 'boolean' },
    pricingGreen: { type: 'boolean' },
    failures: { type: 'array', items: { type: 'string' } },
    details: { type: 'string' },
  },
  required: ['cartGreen', 'orderGreen', 'pricingGreen', 'details'],
}

async function reviewGate(stepName, phaseTitle, charge) {
  const verdict = await agent(
    `Adversarially review the "${stepName}" step's edits. Inspect the ACTUAL diff ` +
    `on disk (git diff of the working tree, unstaged). Default to pass=false if ` +
    `uncertain. ${charge} Return pass + blockers (blockers MUST be [] when pass=true).`,
    { phase: phaseTitle, schema: REVIEW_SCHEMA, agentType: 'general-purpose', effort: 'high' },
  )
  if (!verdict || !verdict.pass) {
    const bl = verdict ? verdict.blockers.join('; ') : 'reviewer returned null'
    throw new Error(`Review gate FAILED for ${stepName}: ${bl}`)
  }
  return verdict
}

// --- Step 1: Discover money-path domain SQL-isms (READ ONLY) ----------------
phase('Discover')
const discover = await agent(
  `Read-only discovery for the §4 MONEY-PATH Postgres SQL port. Scope is ONLY: ` +
  `app/services/cart_service.py, app/services/order_service.py, ` +
  `app/services/product_service.py, app/services/payment_rate_limit_service.py, ` +
  `app/routes/orders.py, app/routes/cart.py. ` +
  `payment_rate_limit_service.py gates EVERY checkout via ` +
  `consume_checkout_order_rate_limit and still has import sqlite3, 8x ` +
  `conn: sqlite3.Connection, BEGIN IMMEDIATE (~line 104) with manual ` +
  `COMMIT/ROLLBACK, and datetime('now', %s)/datetime('now','-2 days') window ` +
  `modifiers (~lines 74, 107) — port it fully; the SQLite window-modifier strings ` +
  `('-15 minutes','-1 hour','-2 days') must become INTERVAL literals. ` +
  `§3 already ran the blind ?->%s codemod and Role-1 datetime('now')->` +
  `CURRENT_TIMESTAMP, and get_db() is now a psycopg pool context manager that ` +
  `commits on clean exit / rolls back on exception. Find every remaining ` +
  `SQLite-ism in these 5 files and classify each: (a) BEGIN IMMEDIATE (the known ` +
  `blocker — 'syntax error at or near "IMMEDIATE"'); (b) Role-2 datetime with ` +
  `intervals, e.g. datetime('now','-N days'|'+N days') needing ` +
  `CURRENT_TIMESTAMP +/- INTERVAL 'N days'; (c) INSERT OR IGNORE needing ` +
  `ON CONFLICT DO NOTHING; (d) cursor.lastrowid needing RETURNING; ` +
  `(e) sqlite3.IntegrityError/Error handlers needing psycopg.errors.* (note the ` +
  `CHECK (stock >= 0) -> InsufficientStock mapping specifically); ` +
  `(f) sqlite3.Connection/Row type hints; (g) strftime/SQLITE_DATETIME_FORMAT ` +
  `round-trips on datetimes. For EACH site give file+line+kind+snippet+the exact ` +
  `PG transform. CRITICAL analysis for txnNotes: examine how BEGIN IMMEDIATE is ` +
  `used in checkout/stock-decrement — determine whether get_db()'s pool already ` +
  `opens a transaction (so the manual BEGIN is redundant and should be REMOVED), ` +
  `or whether nested atomicity needs \`with conn.transaction():\`. The checkout ` +
  `stock-decrement + order-insert MUST stay atomic. Then produce a concrete PLAN. ` +
  `Do NOT edit anything.`,
  { phase: 'Discover', schema: DISCOVER_SCHEMA },
)

// --- Step 2: Port the money path + review -----------------------------------
phase('PortMoneyPath')
const port = await agent(
  `Port the money-path SQL to Postgres from this discovery: ` +
  `${JSON.stringify(discover).slice(0, 7000)}. ` +
  `Edit ONLY: app/services/cart_service.py, app/services/order_service.py, ` +
  `app/services/product_service.py, app/services/payment_rate_limit_service.py, ` +
  `app/routes/orders.py, app/routes/cart.py. ` +
  `payment_rate_limit_service.py gates EVERY checkout via ` +
  `consume_checkout_order_rate_limit and is a KNOWN scope miss the review gate ` +
  `caught — port it fully: (a) remove import sqlite3; (b) all 8x ` +
  `conn: sqlite3.Connection -> psycopg.Connection; (c) the BEGIN IMMEDIATE ` +
  `(~line 104) with its manual COMMIT/ROLLBACK -> use \`with conn.transaction():\` ` +
  `(the delete+check+insert MUST stay atomic — check-then-record is the whole ` +
  `point of this function); (d) datetime('now', '-2 days') (~line 107) -> ` +
  `CURRENT_TIMESTAMP - INTERVAL '2 days'; (e) datetime('now', %s) (~line 74) is ` +
  `the tricky one — the bound value is a SQLite window modifier string ` +
  `('-15 minutes','-1 hour','-2 days'). Postgres cannot bind a bare modifier into ` +
  `datetime(); rewrite the predicate to \`created_at >= CURRENT_TIMESTAMP - %s::interval\` ` +
  `and change the _RateLimitBucket.window_modifier VALUES to POSITIVE Postgres ` +
  `interval strings ('15 minutes','1 hour','2 days') so the subtraction is correct ` +
  `(SQLite used negative offsets added to now; PG subtracts a positive interval). ` +
  `Update every window_modifier literal accordingly (search the whole file — there ` +
  `are several _RateLimitBucket constructions beyond consume_checkout_order_rate_limit). ` +
  `ALSO in order_service.py there are TWO INSERT OR IGNORE sites the port MUST fix ` +
  `(the review gate greps for them): line ~2316 (mark_bank_transfer_paid) and ` +
  `line ~2540 (apply_manual_payment_action), both INSERT OR IGNORE INTO order_emails ` +
  `-> INSERT ... ON CONFLICT DO NOTHING (verify the order_emails conflict target ` +
  `matches the actual unique constraint; if none exists, use a bare ON CONFLICT ` +
  `DO NOTHING only if the table has an inferable arbiter, otherwise flag it as a risk). ` +
  `Apply every transform: BEGIN IMMEDIATE -> rely on get_db()'s transaction (remove ` +
  `the manual BEGIN) OR \`with conn.transaction():\` where nested atomicity is ` +
  `needed — NEVER emit bare "BEGIN IMMEDIATE"; Role-2 datetime -> ` +
  `CURRENT_TIMESTAMP +/- INTERVAL 'N days'; INSERT OR IGNORE -> ON CONFLICT ... ` +
  `DO NOTHING; lastrowid -> RETURNING (use app.database.insert_returning_id if ` +
  `it exists); sqlite3.IntegrityError/Error -> psycopg.errors.* (preserve the ` +
  `CHECK (stock >= 0) -> InsufficientStock exception mapping EXACTLY — this is a ` +
  `data-integrity invariant); sqlite3.Connection/Row hints -> psycopg.Connection; ` +
  `drop strftime round-trips (psycopg adapts datetime directly). The checkout ` +
  `atomicity (decrement stock + insert order + order_items in one transaction, ` +
  `rollback on insufficient stock) MUST be preserved — this is the cardinal ` +
  `money-path invariant. Keep get_db() the single chokepoint; do NOT change public ` +
  `service function signatures (only sqlite3->psycopg type hints). Do NOT touch ` +
  `other domains. Do NOT commit. Report a diff summary with any risks.`,
  { phase: 'PortMoneyPath', schema: DIFF_SCHEMA },
)
await reviewGate('PortMoneyPath', 'ReviewPort',
  `Confirm against the money-path invariants. SCOPE IS 6 FILES: cart_service.py, ` +
  `order_service.py, product_service.py, payment_rate_limit_service.py, ` +
  `routes/orders.py, routes/cart.py. (1) NO "BEGIN IMMEDIATE" remains in ` +
  `any of the 6 files (grep them); manual BEGINs are either removed in favor of ` +
  `get_db()'s txn or replaced by \`with conn.transaction():\` — and checkout still ` +
  `decrements stock + inserts order + order_items ATOMICALLY with rollback on ` +
  `insufficient stock. payment_rate_limit_service._consume_rate_limit must keep its ` +
  `delete+check+insert atomic under \`with conn.transaction():\` (no bare COMMIT/` +
  `ROLLBACK strings). (2) The CHECK (stock >= 0) violation still maps to the ` +
  `InsufficientStock exception (not a raw psycopg error leaking to the route). ` +
  `(3) Every Role-2 datetime uses CURRENT_TIMESTAMP +/- INTERVAL (or ` +
  `- %s::interval for the parameterized window in payment_rate_limit_service); ` +
  `no datetime('now' remains anywhere. Confirm the window_modifier literals were ` +
  `flipped from negative SQLite modifiers ('-15 minutes') to POSITIVE PG intervals ` +
  `('15 minutes') so CURRENT_TIMESTAMP - %s::interval computes the same window. ` +
  `(4) No INSERT OR IGNORE remains — SPECIFICALLY re-verify the two order_service.py ` +
  `sites (mark_bank_transfer_paid ~2316, apply_manual_payment_action ~2540) are now ` +
  `INSERT ... ON CONFLICT DO NOTHING. No cursor.lastrowid, no sqlite3.IntegrityError/` +
  `Error/Connection/Row, no "import sqlite3" remains in these 6 files. (5) No public ` +
  `service signature changed (diff the def lines). (6) Only the 6 in-scope files ` +
  `changed — no other domain touched. Re-grep ALL 6 files for: "BEGIN IMMEDIATE", ` +
  `"datetime('now'", "INSERT OR IGNORE", "lastrowid", "sqlite3". Report blockers ` +
  `for any hit.`)

// --- Step 3: Green-test gate (READ ONLY assessment; runs pytest) ------------
phase('GreenGate')
const gate = await agent(
  `Assess the money-path port against live Postgres (compose up, alembic head). ` +
  `Run each of these with \`.venv/bin/pytest <file> -q -p no:xdist\` and report ` +
  `pass/fail + the failing test ids and root-cause error lines: ` +
  `(1) tests/test_pricing.py (must STAY green — regression check); ` +
  `(2) tests/test_cart_routes.py (was failing on BEGIN IMMEDIATE — must now be ` +
  `green); (3) tests/test_order_routes.py; (4) tests/test_payment_rate_limit_service.py ` +
  `(payment_rate_limit_service is now in scope — the BEGIN IMMEDIATE + parameterized ` +
  `interval port must be green here); also any cart/order/product SERVICE ` +
  `test file you find (e.g. test_cart_service.py, test_order_service.py, ` +
  `test_product_service.py) — run those too and fold into orderGreen/cartGreen. ` +
  `Do NOT fix code — this is assessment. For each failure give the file::test and ` +
  `the psycopg/error line so the human can triage. Report cartGreen, orderGreen, ` +
  `pricingGreen, failures, details.`,
  { phase: 'GreenGate', schema: GATE_SCHEMA },
)

return {
  discover: { siteCount: discover.sites.length, txnNotes: discover.txnNotes, plan: discover.plan },
  port,
  gate,
  reviewModel: 'PortMoneyPath passed an adversarial review gate (chain halts on fail).',
  humanGate: 'Review the money-path diff + green-gate result before committing. Nothing committed. If cart/order/pricing are green, commit the money-path slice; then the next §4 slice is the remaining domains (admin/analytics/accounting/econt/etc.).',
}
