---
description: "Exhaustive multi-agent code review — finds ALL bugs, then all warnings, then suggestions. Tests each finding, explains each finding, and optionally auto-fixes."
argument-hint: "[pr-url | file-path | --diff-only]"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Agent
  - Glob
  - Grep
  - WebFetch
  - TaskCreate
  - TaskUpdate
  - TaskList
  - AskUserQuestion
---

<objective>
Exhaustive code review that finds EVERY issue — no caps, no filters, no premature pruning.

The philosophy: a good review finds all the problems first, then helps you understand and fix them. This skill operates in three waves:

1. **FIND ALL** — Parallel expert agents sweep the diff with NO limit on findings. Every bug, every warning, every suggestion surfaces.
2. **TEST ALL** — Each finding is verified: can we reproduce the scenario? Does the code actually misbehave? False positives are killed with evidence.
3. **EXPLAIN ALL** — Surviving findings get clear, contextual explanations: what breaks, why, and how to fix it.

After the report, the user chooses: read and fix manually, or let the skill auto-apply fixes.
</objective>

<context>
## Project Identity

This is **AtelierMarie** — a luxury candle e-commerce platform for a small family business. Two strict layers:

- **Layer 1 (Production E-Commerce):** Products, cart, checkout, orders, auth, admin. SQLite only (WAL mode). Must work perfectly if Layer 2 is OFF. All responses <200ms.
- **Layer 2 (Analytics & ML Sandbox):** Event collection (fire-and-forget JSONL), DuckDB analytics, ML recommendations. Can crash without affecting the store.

**The cardinal rule:** Layer 1 code NEVER imports from Layer 2 modules (`app/analytics/`, `app/ml/`).

**Tech stack:**
- Backend: Python 3.11, FastAPI, Pydantic 2, Uvicorn
- Database: SQLite (WAL mode) — system of record; DuckDB for analytics only
- Auth: Google OAuth 2.0 + JWT (PyJWT)
- Frontend: Next.js 14 (App Router, TypeScript, Tailwind CSS)
- Hosting: Oracle Cloud Free Tier (single VPS), Nginx, systemd

## Standards Authority

The project's CLAUDE.md is the single source of truth for coding standards. The `openspec/changes/` directory defines feature specifications. Every reviewer MUST internalize these before issuing findings.

## Input Parsing

```
$ARGUMENTS parsing:
- Empty or "--diff-only"     → DIFF mode
- Matches /pull/\d+/         → PR mode (extract PR number)
- Matches a file path        → FILE mode (verify with test -f)
```
</context>

<process>

## PHASE 0 — Gather Context

### 0a. Determine mode and get the diff

**DIFF mode (default):**
```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
DIFF_CONTENT=$(git diff HEAD)
if [ -z "$DIFF_CONTENT" ]; then
  DIFF_CONTENT=$(git diff --cached)
fi
if [ -z "$DIFF_CONTENT" ]; then
  echo "No changes to review."
  exit 0
fi
DIFF_STAT=$(echo "$DIFF_CONTENT" | diffstat 2>/dev/null || git diff --stat HEAD)
```

**PR mode:**
```bash
PR_META=$(gh pr view $PR_NUMBER --json title,body,state,baseRefName,headRefName,commits)
DIFF_CONTENT=$(gh pr diff $PR_NUMBER)
DIFF_STAT=$(gh pr diff $PR_NUMBER --stat 2>/dev/null)
```

**FILE mode:**
```bash
DIFF_CONTENT=$(cat "$ARGUMENTS")
DIFF_STAT="Single file: $ARGUMENTS"
```

### 0b. Read project standards

Read `CLAUDE.md` and identify relevant `openspec/changes/*/design.md` files for the changed modules.

### 0c. Classify changed files

Categorize into: `backend_services`, `backend_routes`, `backend_models`, `backend_middleware`, `backend_database`, `backend_config`, `layer2_analytics`, `layer2_ml`, `frontend_components`, `frontend_lib`, `frontend_config`, `test_files`, `deploy_files`, `spec_files`.

---

## PHASE 1 — FIND ALL (Unrestricted Parallel Sweep)

Spawn ALL applicable council members in parallel. Each agent is instructed to report EVERY finding — **no limit on count, no confidence threshold, no filtering**. The philosophy: find everything now, verify later.

### Council Members & Activation

| Reviewer | Activation Rule |
|----------|----------------|
| E-Commerce Architect | ALWAYS |
| Senior Python Developer | `backend_*` OR `test_files` non-empty |
| Security Engineer | ALWAYS |
| QA/Test Engineer | `backend_*` OR `test_files` non-empty |
| Frontend Developer | `frontend_*` non-empty |
| Layer Boundary Auditor | `layer2_*` non-empty OR any file imports from `app.analytics`/`app.ml` |

Minimum 3 reviewers always active (Architect + Security + Python).

### Agent Prompt Template

Each agent receives:

```
You are a {ROLE_NAME} reviewing code for AtelierMarie — a luxury candle e-commerce platform.

## CRITICAL INSTRUCTION: FIND EVERYTHING

You must report EVERY issue you see. Do NOT self-filter. Do NOT cap your findings at any number.
Do NOT dismiss something as "minor" — report it and label its severity accurately.

The verification step comes LATER. Your job now is COMPREHENSIVE DISCOVERY.

Think about:
1. What is the author trying to do?
2. What invariants must hold for correctness?
3. What breaks if assumptions change?
4. What would a principal engineer flag in a production review?

Do NOT report formatting/style that `ruff` catches.
Focus on: logic errors, architectural mistakes, security gaps, missing edge cases, incorrect abstractions, layer violations, data integrity risks.

## Project Standards
{CLAUDE_MD_RELEVANT_SECTIONS}

## Related Spec
{RELEVANT_OPENSPEC_DESIGN}

## Your Review Checklist
{ROLE_SPECIFIC_CHECKLIST — see below}

## Changed Files
{DIFF_STAT}

## Full Diff
{DIFF_CONTENT}

## Output Format

For EACH finding (report ALL, no limit):

### Finding N
- **Severity**: BLOCKER | WARNING | SUGGESTION
- **Category**: layer-violation | architecture | logic-bug | security | performance | data-integrity | state-machine | session | stock | test-gap | frontend | spec-deviation
- **File**: path/to/file.py
- **Line**: line number or range
- **Title**: One-line summary
- **Detail**: Why this is a problem — what scenario breaks
- **Evidence**: The specific code or pattern that proves it
- **Suggested Fix**:
  ```
  corrected code or approach
  ```

Report EVERY issue. Do not self-censor. If uncertain, report it with a note "Confidence: uncertain — needs verification."
```

### Role Checklists (embedded in each agent's prompt)

**E-Commerce Architect:**
- Layer boundary violations (Layer 1 importing from Layer 2)
- Layer 2 error propagation to Layer 1
- Order state machine validity (pending→confirmed→shipped→delivered; cancel from pending/confirmed only)
- Stock integrity (atomic decrement at checkout, CHECK constraint, restore on cancel)
- Session model (anonymous-first, session rotation on logout, cart tied to session)
- Price handling (cents as int, `price_cents` naming, no floats in money path)
- Order snapshots immutability (order_items stores name + price at purchase time)
- Soft delete (is_active flag, never DELETE FROM products)
- Stock validation on cart add (409 Conflict)
- Service layer pattern (thin routes, fat services)
- API versioning (/v1/ prefix)
- Response time (no N+1, no unbounded queries, no blocking I/O in request path)
- Spec compliance with openspec
- GDPR NULL-ification (not cascade delete)

**Senior Python Developer:**
- Pydantic 2 patterns (model_validate, model_dump)
- Type annotations (str | None, list[str])
- Pydantic Settings for config (never os.environ/os.getenv)
- FastAPI dependency injection
- Exception handling (custom exceptions, raise from, no bare except)
- DB context managers (with get_db() as conn:)
- Parameterized SQL (? placeholders, never f-strings)
- Naming conventions (snake_case, PascalCase for classes, UPPER_SNAKE_CASE for constants)
- Module structure (thin routes, fat services, models separate)
- Literal for constrained strings
- Import order and no circular imports

**Security Engineer:**
- No secrets in source
- Input validation at API boundaries
- SQL injection prevention
- No eval/exec/pickle.loads/yaml.unsafe_load on untrusted input
- Auth checks on admin routes
- JWT validation (audience, issuer, expiry)
- Session security (UUID4, HttpOnly, rotation)
- CORS restrictive
- Path traversal prevention
- Error message information leakage
- OAuth validation
- Constant-time API key comparison (hmac.compare_digest)
- File upload validation
- No mass assignment
- Cookie attributes (Secure, HttpOnly, SameSite=Lax)

**QA/Test Engineer:**
- Every new public function has tests
- Test isolation (in-memory SQLite, fresh TestClient per test)
- Edge cases covered (empty cart, out-of-stock, invalid transitions, expired session)
- Order state machine test coverage (all valid AND invalid transitions)
- Stock race condition handling
- Auth path testing (JWT, API key, unauthenticated)
- Cart operations tested (add with 0 stock → 409, quantity limits)
- CSV import edge cases
- Pydantic validation edge cases
- No time.sleep in tests
- Test naming pattern (test_<behavior>_<scenario>)
- Coverage not regressed
- Layer 2 failure isolation tested

**Frontend Developer:**
- TypeScript strict (no any)
- API client typed from lib/types.ts
- Mock/real API identical shapes
- Price formatting (cents → display currency)
- Loading/error states
- Responsive design
- Accessibility (semantic HTML, ARIA, keyboard nav)
- Optimistic cart updates with rollback
- Form validation mirrors server rules
- next/image with sizes + alt
- No unnecessary re-renders
- Tailwind design tokens (no arbitrary values)
- Server Components vs Client Components correctly used
- No hardcoded URLs

**Layer Boundary Auditor:**
- No Layer 1 imports from app.analytics/app.ml
- Layer 2 catches ALL its own exceptions
- Event collection fire-and-forget
- DuckDB timeouts, no event loop blocking
- Recommendation fallback chain
- Feature flags for disabling Layer 2
- No shared DB connections
- JSONL atomic writes (O_APPEND)
- Optional-import guards for Layer 2 dependencies

---

## PHASE 2 — TEST ALL (Verification Sweep)

After all agents return, collect ALL findings into a master list. Then verify each one:

### 2a. Deduplicate

Group findings by `(file, line-range, category)`. When multiple reviewers flag the same thing:
- Keep the most detailed version
- Merge evidence from all reviewers
- Mark as `🤝 Consensus` (higher confidence)

### 2b. Verify each finding

For each unique finding, determine if it's real:

1. **Read the actual code** (not just the diff) — does the surrounding context change the interpretation?
2. **Check if there's already a guard** — does another part of the code prevent this scenario?
3. **Check the spec** — is this behavior actually intentional per openspec?
4. **Trace the data flow** — does the bug scenario actually reach this code path?

Mark each finding:
- ✅ **CONFIRMED** — verified real with evidence
- ❌ **FALSE POSITIVE** — explain why it's not actually an issue
- ⚠️ **UNCERTAIN** — cannot confirm or deny; include in report with caveat

**Kill false positives aggressively.** Only confirmed and uncertain findings proceed.

### 2c. Run project tests

```bash
pytest --tb=short -q 2>&1 | tail -30
```

Note which tests pass/fail. If a finding predicts a failure, check if tests already catch it.

---

## PHASE 3 — EXPLAIN ALL (Structured Report)

Generate the full report with ALL surviving findings, organized by severity:

```markdown
# 🕯️ AtelierMarie — Exhaustive Code Review

**Mode**: {diff | PR #N: "title" | file: path/to/file.py}
**Branch**: {branch-name}
**Verdict**: {🔴 HAS BUGS | 🟡 WARNINGS ONLY | 🟢 CLEAN}

---

## Summary

| Severity | Count |
|----------|-------|
| 🔴 BLOCKER (bugs) | N |
| 🟡 WARNING | N |
| 💡 SUGGESTION | N |

**Council Members**: {list}
**Consensus Findings**: {N}
**False Positives Killed**: {N}
**Test Suite**: {✅ passing | ❌ N failures}

---

## 🔴 BUGS (All Blockers)

### 1. {Title}
**File**: `{file}:{line}`
**Category**: {tag} | **Found by**: {reviewer(s)} {🤝 if consensus}
**Status**: ✅ CONFIRMED

**What breaks:**
{Clear explanation of the failure scenario — what input or state triggers this, what goes wrong, what the user/system experiences}

**Evidence:**
```{language}
{the problematic code}
```

**Why it's wrong:**
{Explain the invariant that's violated and why the code doesn't uphold it}

**Fix:**
```{language}
{corrected code}
```

---

## 🟡 WARNINGS (All)

### N. {Title}
**File**: `{file}:{line}`
**Category**: {tag} | **Found by**: {reviewer(s)}
**Status**: ✅ CONFIRMED | ⚠️ UNCERTAIN

**What's wrong:**
{Explanation}

**Risk if ignored:**
{What could go wrong over time}

**Fix:**
```{language}
{corrected code}
```

---

## 💡 SUGGESTIONS (All)

### N. {Title}
**File**: `{file}:{line}`
**Category**: {tag}

**Current approach:**
{What the code does now}

**Better approach:**
{What would be cleaner/faster/more maintainable and why}

```{language}
{suggested code}
```

---

## 📊 Verification Summary

| # | Finding | Verified | Method |
|---|---------|----------|--------|
| 1 | {title} | ✅ CONFIRMED | {how verified} |
| 2 | {title} | ❌ FALSE POSITIVE | {why} |
| ... | ... | ... | ... |

## ❌ Killed False Positives

{List each false positive and why it was dismissed — for transparency}
```

---

## PHASE 4 — FIX OPTION

After presenting the full report, ask the user:

```
"I found N bugs, M warnings, and K suggestions.

Would you like me to:
1. 🔧 **Auto-fix all** — Apply fixes for all confirmed bugs and warnings
2. 🐛 **Fix bugs only** — Apply fixes for blockers/bugs only
3. 🎯 **Cherry-pick** — I'll list them numbered, you tell me which to fix
4. 📖 **Read only** — No changes, just the report

(I'll show you each edit before applying and run tests after.)"
```

### If the user chooses to fix:

**The Fix Loop — fight until green:**

The skill does NOT give up after one attempt. It loops until the codebase is truly fixed:

```
FOR each finding to fix:
  1. Read the target file (full context around the issue)
  2. Apply the fix using Edit
  3. Run `pytest --tb=short -q` and `ruff check .`
  4. IF tests pass and ruff clean → ✅ mark fixed, move to next finding
  5. IF tests fail or ruff errors:
     a. Read the failure output carefully
     b. Diagnose WHY the fix broke something
     c. Try a DIFFERENT approach (not the same fix again)
     d. Apply the new attempt
     e. Run tests again
     f. REPEAT up to 5 attempts per finding
  6. IF after 5 attempts still failing:
     a. Revert ALL attempts for this finding back to the original code
     b. Report: "Could not fix #{N} — tried 5 approaches, all failed tests. Here's what I learned: {diagnosis}"
     c. Move to next finding
```

**Key rules for the fix loop:**
- Each retry must be a DIFFERENT strategy, not the same code tweaked slightly
- After each attempt, read the FULL test output — understand the failure, don't guess
- If fixing finding A breaks a test that finding B's fix would also touch, fix them together
- If a fix introduces a NEW issue not in the original report, fix that too (don't leave new bugs)
- Ruff issues from the fix are fixed inline (they're trivial — just do it)
- The loop ONLY stops when: tests pass ✅, or 5 attempts exhausted

**After ALL findings are processed:**

1. Run final `pytest --tb=short -q` and `ruff check .`
2. If ANYTHING still fails, diagnose and fix (same loop logic)
3. Show final status:

```markdown
## ✅ Fix Summary

| # | Finding | Status | Attempts |
|---|---------|--------|----------|
| 1 | {title} | ✅ Fixed | 1 |
| 2 | {title} | ✅ Fixed | 3 |
| 3 | {title} | ❌ Could not fix | 5 (exhausted) |

**Test suite**: ✅ all passing (or ❌ N failures remaining)
**Ruff**: ✅ clean
**Files changed**: {list}
```

---

</process>

<guardrails>

## Key Principles

- **NO CAPS ON FINDINGS** — Report everything. The user decides what matters, not the tool.
- **VERIFY BEFORE REPORTING** — Every finding is tested. False positives are killed with evidence and listed transparently.
- **EXPLAIN, DON'T JUST FLAG** — Each finding includes what breaks, why, and how to fix it. The user should understand the issue deeply.
- **FIX IS OPTIONAL** — The auto-fix is offered, never forced. The user stays in control.
- **FIGHT UNTIL GREEN** — When fixing, don't give up on first failure. Loop: fix → test → diagnose → retry with a different approach. Up to 5 attempts per finding before declaring defeat.
- **TESTS ARE THE TRUTH** — The fix isn't done until tests pass. Period.
- **LAYER BOUNDARY IS SACRED** — A Layer 1 import from Layer 2 is ALWAYS a blocker. No exceptions.

## What This Does NOT Do

- Does not replace linters (ruff handles formatting/style)
- Does not invent standards (every finding traces to CLAUDE.md, openspec, or a concrete engineering principle)
- Does not silently skip issues (if something is dismissed, it's listed under "Killed False Positives" with reasoning)
- Does not modify code without user consent
- Does not leave the codebase broken (loops until tests pass — only gives up after 5 failed attempts per finding, and reverts those back to original)

## Quality Hierarchy

When reporting, follow this priority order within each severity level:
1. Layer boundary violations
2. Data integrity (money, stock, order snapshots)
3. Security (injection, auth bypass, credential exposure)
4. Logic bugs (state machine, race conditions, edge cases)
5. Spec deviations
6. Test gaps
7. Performance
8. Style/patterns (only if causes maintenance burden)

</guardrails>