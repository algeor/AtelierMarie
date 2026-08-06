// =============================================================================
// Postgres Migration — Phase 1 sweeps + §3 Connection Layer  (WITH REVIEW GATES)
// =============================================================================
// HOW TO LAUNCH (after leaving explore mode):
//   Say:  ultracode — run the postgres-migration Phase-1 + §3 workflow
//   or invoke the Workflow tool with { scriptPath: "<this file>" }.
//   The `ultracode` keyword (or "use a workflow") authorizes the tool to fire.
//
// REVIEW MODEL:
//   Every EDITING step is followed by an adversarial reviewer (a fresh
//   code-reviewer agent) that inspects the ACTUAL on-disk diff and returns a
//   pass/fail verdict + blockers. On fail the reviewer THROWS, which halts the
//   chain — a broken diff never feeds the next step. The read-only Audit and
//   the final Verify have no reviewer (Audit makes no edits; Verify IS the
//   review).
//
// WHAT IT STILL DOES NOT DO:
//   - No auto-commit, no merge. Editing agents work on the current branch.
//   - It cannot pause for YOU mid-run (workflows run to completion in the
//     background). Per-step reviewers raise confidence and stop the chain early,
//     but the final human review of the ConnLayer diff is still yours to do.
//
// PREREQUISITES the workflow assumes are already true:
//   - local Postgres up (compose.yml) and `alembic upgrade head` applied,
//     for the Verify step to boot against.
// =============================================================================

export const meta = {
  name: 'pg-migration-phase1-and-conn-reviewed',
  description: 'PG migration slice 1 with review gates: %%-audit → ?→%s codemod +review → Role-1 datetime sweep +review → psycopg get_db/pool +review → boot-on-PG verify',
  phases: [
    { title: 'Audit' },
    { title: 'Codemod' },
    { title: 'ReviewCodemod' },
    { title: 'DatetimeSweep' },
    { title: 'ReviewDatetime' },
    { title: 'ConnLayer' },
    { title: 'ReviewConnLayer' },
    { title: 'Verify' },
  ],
}

const AUDIT_SCHEMA = {
  type: 'object',
  properties: {
    sites: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          line: { type: 'integer' },
          snippet: { type: 'string' },
          reason: { type: 'string' }, // LIKE pattern | strftime | other literal %
        },
        required: ['file', 'line', 'snippet', 'reason'],
      },
    },
    total: { type: 'integer' },
  },
  required: ['sites', 'total'],
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
    blockers: { type: 'array', items: { type: 'string' } }, // must be [] when pass=true
    notes: { type: 'string' },
  },
  required: ['pass', 'blockers'],
}

const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    booted: { type: 'boolean' },
    migrationHeadCheckPasses: { type: 'boolean' },
    details: { type: 'string' },
    blockers: { type: 'array', items: { type: 'string' } },
  },
  required: ['booted', 'migrationHeadCheckPasses', 'details'],
}

// Gate helper: run an adversarial reviewer on the current on-disk diff. Throws
// on fail so the pipeline halts before the next editing step runs.
async function reviewGate(stepName, phaseTitle, chargeToReviewer) {
  const verdict = await agent(
    `Adversarially review the "${stepName}" step's edits. Inspect the ACTUAL diff ` +
    `on disk (git diff of the working tree). Default to pass=false if uncertain. ` +
    `${chargeToReviewer} Return pass + blockers (blockers MUST be [] when pass=true).`,
    { phase: phaseTitle, schema: REVIEW_SCHEMA, agentType: 'general-purpose', effort: 'high' },
  )
  if (!verdict || !verdict.pass) {
    const bl = verdict ? verdict.blockers.join('; ') : 'reviewer returned null'
    throw new Error(`Review gate FAILED for ${stepName}: ${bl}`)
  }
  return verdict
}

// --- Step 1: %%-literal audit (READ ONLY — blocking prerequisite) -----------
phase('Audit')
const audit = await agent(
  `Read-only audit. In app/ (Python), find every bare "%" that is a SQL literal, ` +
  `NOT a psycopg parameter marker: LIKE patterns (~20 sites), strftime format ` +
  `strings (~33), and any other literal % inside SQL strings. Under psycopg these ` +
  `must become "%%". Do NOT edit anything. Return the full list.`,
  { phase: 'Audit', schema: AUDIT_SCHEMA },
)

// --- Step 2: ?→%s codemod  + review gate ------------------------------------
phase('Codemod')
const codemod = await agent(
  `Flip SQLite "?" placeholders to psycopg "%s" across app/ (~896 lines). ` +
  `FIRST double the literal-% sites from this audit so they survive: ` +
  `${JSON.stringify(audit.sites)}. This is a single lexical flip of ? → %s inside ` +
  `SQL strings ONLY — do not touch "?" in comments, regex, f-strings, or non-SQL ` +
  `contexts. CRITICAL — natural-language "?" that must stay literal (do NOT flip): ` +
  `question marks INSIDE quoted string DATA, including FAQ question text such as ` +
  `"Where are your candles made?", "Will my candle look exactly like the photos?", ` +
  `and the SQL string-literal WHERE values 'Do you accept returns?' / ` +
  `'Приемате ли връщания?' in app/database.py's faq_items migrations. Those "?" are ` +
  `data, not placeholders. Only flip "?" that psycopg would bind as a parameter. ` +
  `ALSO CRITICAL — dynamic IN-list builders: NEVER rewrite ",".join("?" * len(x)) ` +
  `to ",".join("%s" * len(x)) — "%s" is 2 chars so "%s"*n gives "%s%s%s" and the ` +
  `join yields the malformed "%,s,%,s". Use ",".join("%s" for _ in x) instead ` +
  `(the idiom already correct in product_service.py). Known sites: ` +
  `analytics_service.py:745/773/886, order_service.py:1238. ` +
  `Do NOT commit. Report a diff summary a human will review before merge.`,
  { phase: 'Codemod', schema: DIFF_SCHEMA },
)
await reviewGate('Codemod', 'ReviewCodemod',
  `Confirm: every %%-audit site listed was actually doubled; NO "?" was flipped ` +
  `inside a comment, regex, f-string, or other non-SQL context; and no SQL "?" ` +
  `placeholder was missed. Re-grep the tree to check for stray unconverted "?" in ` +
  `SQL strings and for single "%" still bare in LIKE/strftime.`)

// --- Step 3: Role-1 datetime('now') sweep  + review gate --------------------
phase('DatetimeSweep')
const dtSweep = await agent(
  `Replace ONLY Role-1 "stamp now" uses of datetime('now') / date('now') with ` +
  `CURRENT_TIMESTAMP / CURRENT_DATE across app/ (~205 + 5 sites). Role-1 = ` +
  `SET updated_at=datetime('now') and VALUES(...,datetime('now')). LEAVE ALONE ` +
  `Role-2 "now ± interval" sites (WHERE created_at < datetime('now', ?)) — those ` +
  `are Phase-2 semantic rewrites (design Decision 11); flag them, don't touch them. ` +
  `Do NOT commit. Report the diff summary and the list of Role-2 sites left for later.`,
  { phase: 'DatetimeSweep', schema: DIFF_SCHEMA },
)
await reviewGate('DatetimeSweep', 'ReviewDatetime',
  `Confirm: ONLY Role-1 stamp-now sites were changed; NO Role-2 "now ± interval" ` +
  `site (datetime('now', <modifier>)) was touched — those must remain for Phase 2. ` +
  `Re-grep for any remaining datetime('now') / date('now') and classify each as ` +
  `correctly-left Role-2 vs missed Role-1.`)

// --- Step 4: §3 connection layer flip  + review gate ------------------------
phase('ConnLayer')
const conn = await agent(
  `Implement §3 (design Decisions 2, 2a, 3, 12) in app/database.py and callers: ` +
  `(3.2) replace get_db() with a psycopg ConnectionPool-backed context manager — ` +
  `pool as a MODULE-GLOBAL in app/database.py (mirror the old _db_path global), ` +
  `commit on success / rollback on error; (2a/12) pool configure= callback sets ` +
  `row_factory=dict_row and TimeZone=UTC on every connection once; (3.1) init_db ` +
  `becomes Postgres connectivity + a migration-head check that fails startup when ` +
  `the DB is behind Alembic head (compare DB current revision vs script-dir head); ` +
  `(3.3) keyed row access; (3.4) helpers for = ANY(%s), RETURNING id; (3.5) psycopg ` +
  `exception classes replacing sqlite3.IntegrityError/Error catches; (3.7) remove ` +
  `WAL/FTS5-reset/PRAGMA/SQLite-backfill code paths. Keep the ~479 conn-taking ` +
  `service signatures UNCHANGED (get_db stays the single chokepoint). Do NOT port ` +
  `domain SQL correctness — that is §4. Do NOT commit. Report a diff summary.`,
  { phase: 'ConnLayer', schema: DIFF_SCHEMA },
)
await reviewGate('ConnLayer', 'ReviewConnLayer',
  `Confirm against design Decisions 2/2a/3/12: the pool is a module-global (not ` +
  `app.state/contextvar); get_db() commits on success and rolls back on error; the ` +
  `configure= callback sets dict_row AND TimeZone=UTC exactly once per connection; ` +
  `init_db performs a migration-head check that FAILS startup when behind head; the ` +
  `~479 conn-taking service signatures are UNCHANGED; and no SQLite-only code ` +
  `(PRAGMA/WAL/FTS5 reset/sqlite3 exception catches) remains in the connection layer.`)

// --- Step 5: Verify the app boots on Postgres (READ ONLY assessment) --------
// TESTING SCOPE FOR THIS SLICE: boot + migration-head + one read endpoint ONLY.
// Do NOT add a `make test-backend` gate here — the test fixtures (conftest.py)
// are still SQLite until §6 ports them, so the full suite would fail en masse
// against psycopg app code and prove nothing. The green-test gate belongs to the
// §4/§6 workflow, per design Migration Plan step 5 (Phase-2 per-domain green gate).
phase('Verify')
const verify = await agent(
  `Verify the slice end-to-end. Assume a local Postgres is up (compose.yml) and ` +
  `alembic upgrade head has run. Boot the app (.venv/bin/uvicorn app.main:app ` +
  `--port 8000) and confirm: (a) it starts without SQLite/psycopg errors, ` +
  `(b) the migration-head check passes on a migrated DB and FAILS on a stale one, ` +
  `(c) a trivial read endpoint responds. Do NOT fix code — this is assessment. ` +
  `Report booted / migrationHeadCheckPasses / blockers. Note: domain tests are ` +
  `NOT expected green yet (that is §4/§6); only boot + head-check are in scope.`,
  { phase: 'Verify', schema: VERIFY_SCHEMA },
)

return {
  auditSites: audit.total,
  codemod,
  datetimeSweep: dtSweep,
  connLayer: conn,
  verify,
  reviewModel: 'Each editing step passed an adversarial review gate (chain halts on fail).',
  humanGate: 'Review the reported diffs (codemod, datetime, connLayer) and the verify result before committing or merging. Nothing was committed.',
}
