export const meta = {
  name: 'implement-r2-migration',
  description: 'Implement the migrate-image-storage-to-r2 change: R2 object storage service, image/video write+delete paths, backfill script, tests — with a per-phase code-review gate.',
  phases: [
    { title: 'Phase 0: Storage service + config', detail: 'boto3 dep, R2 config, object_storage_service.py + its tests (barrier — lands on main first)' },
    { title: 'Phase 0 review', detail: 'code-review the storage service diff' },
    { title: 'Phase 1: Media paths', detail: 'image path + video path in parallel isolated worktrees' },
    { title: 'Phase 1 review', detail: 'code-review the merged media-path diff' },
    { title: 'Phase 2: Backfill + orphan fix', detail: 'backfill script + product deactivation image cleanup' },
    { title: 'Phase 2 review', detail: 'code-review backfill + deactivation diff' },
    { title: 'Phase 3: Tests + gate', detail: 'update media tests, run full make test/lint until green' },
    { title: 'Phase 3 review', detail: 'final code-review over the test + full diff' },
  ],
}

// ---- shared context every agent needs ----
const REPO = '/Users/i748006/Desktop/Learning/Aleks/AtelierMarie'
const SPEC_CTX = `
This implements the OpenSpec change 'migrate-image-storage-to-r2'. Read these before editing:
- ${REPO}/openspec/changes/migrate-image-storage-to-r2/proposal.md
- ${REPO}/openspec/changes/migrate-image-storage-to-r2/design.md   (the 9 Decisions are binding)
- ${REPO}/openspec/changes/migrate-image-storage-to-r2/specs/**/spec.md
- ${REPO}/openspec/changes/migrate-image-storage-to-r2/tasks.md
- ${REPO}/CLAUDE.md   (coding standards; pydantic-settings only, no os.getenv; prices in cents; layer isolation)

BINDING DECISIONS (from design.md):
- Single object storage service (app/services/object_storage_service.py) wraps boto3 against R2. boto3 imported ONLY there.
- DB stores FULL public R2 URLs (https://{public-base}/products/...). No schema change.
- Object keys reuse existing stems under 'products/': {product_id}_{image_id}.webp / _thumb.webp / _zoom.webp,
  {product_id}_{video_id}_video.mp4 / _poster.webp. Validate product_id against slug allowlist ^[a-z0-9][a-z0-9-]*[a-z0-9]$.
- Upload-to-R2 BEFORE DB write; wrap botocore errors as MediaStorageError; never leak botocore.
- Delete = best-effort R2 DeleteObject; handle legacy /static (disk unlink) + external URLs (skip) during transition.
- Video: transcode locally in video_upload_temp_path, upload ONLY outputs (mp4 video/mp4, poster image/webp) to R2.
- DEAD SIMPLE: public bucket, no visibility flag, no signed URLs, zoom stays pre-baked.
- Config additions: r2_bucket, r2_endpoint_url, r2_access_key_id, r2_secret_access_key, r2_public_base_url (env R2_*, empty defaults).
- Tests use a fake in-memory storage backend (key->bytes), NOT a live bucket. No moto required.
- Commands: use .venv/bin/ prefix (never activate). Tests: .venv/bin/pytest. Lint: .venv/bin/ruff.
`

const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    blockers: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          summary: { type: 'string' },
          why: { type: 'string' },
        },
        required: ['file', 'summary', 'why'],
      },
    },
    nits: { type: 'array', items: { type: 'string' } },
    verdict: { type: 'string', enum: ['pass', 'needs_fixes'] },
  },
  required: ['blockers', 'verdict'],
}

// review a phase's diff; loop a fix agent until pass or 2 rounds
async function reviewGate(phaseName, reviewFocus, diffHint) {
  for (let round = 1; round <= 2; round++) {
    const review = await agent(
      `${SPEC_CTX}\nYou are a code reviewer for AtelierMarie. Review the working-tree changes for the "${phaseName}" phase.\n` +
        `Inspect the diff (git diff / git status in ${REPO}${diffHint ? '; focus files: ' + diffHint : ''}).\n` +
        `Prioritize in order: (1) LAYER BOUNDARY — critical-path code (cart/checkout/order/payment) must NOT import object_storage_service; boto3 imported ONLY in object_storage_service.py. (2) DATA INTEGRITY — upload-before-DB-write ordering, no DB row referencing a failed upload. (3) SECURITY — slug allowlist on keys, no SQL string-formatting, no credential leaks. (4) SPEC COMPLIANCE vs the binding decisions. (5) ${reviewFocus}. (6) tests present for new paths.\n` +
        `Only flag real blockers (would break behavior, violate a binding decision, or a security/data bug). Return verdict "pass" if the phase is sound.`,
      { label: `review:${phaseName} r${round}`, phase: `${phaseName} review`, schema: REVIEW_SCHEMA, effort: 'high' }
    )
    if (!review || review.verdict === 'pass' || (review.blockers || []).length === 0) {
      log(`${phaseName}: review passed (round ${round})`)
      return review
    }
    log(`${phaseName}: ${review.blockers.length} blocker(s) round ${round} — dispatching fix`)
    await agent(
      `${SPEC_CTX}\nApply fixes to the working tree in ${REPO} for these code-review blockers from the "${phaseName}" phase. Fix ONLY these, do not refactor unrelated code. Re-run the relevant tests with .venv/bin/pytest after fixing.\n\nBLOCKERS:\n${JSON.stringify(review.blockers, null, 2)}`,
      { label: `fix:${phaseName} r${round}`, phase: `${phaseName} review`, effort: 'high' }
    )
  }
  log(`${phaseName}: exhausted 2 fix rounds — proceeding, flag for human review`)
  return null
}

// ================= PHASE 0 — barrier, on main =================
phase('Phase 0: Storage service + config')
await agent(
  `${SPEC_CTX}\nImplement tasks group 1 (Dependencies & configuration) and group 2 (Object storage service) from tasks.md, in the MAIN working tree at ${REPO}.\n` +
    `Concretely:\n` +
    `- Add boto3 to pyproject.toml; add R2_* settings to app/config.py (empty-string defaults); add vars to .env.example and .env.docker.example and compose.yml backend env.\n` +
    `- Create app/services/object_storage_service.py: lazily-constructed module-cached boto3 S3 client (endpoint_url, region_name="auto", S3v4) from config; functions upload_bytes(key,data,content_type)->public_url, delete_object(key) (idempotent), public_url(key) (normalize trailing slash), object_key_for(...) helpers reusing existing stems under products/ and validating product_id slug allowlist. Add MediaStorageError and wrap botocore errors. Raise a clear config error from the write path when R2_* unset.\n` +
    `- Add a test seam: fake in-memory backend injectable via set_backend()/monkeypatch.\n` +
    `- Write tests/test_object_storage_service.py: key derivation + slug allowlist, public-URL join, wrapped botocore error, idempotent delete.\n` +
    `Run .venv/bin/ruff check on new/changed files and .venv/bin/pytest tests/test_object_storage_service.py -q. Do NOT touch image/video services yet. Report the storage service's public function signatures exactly, so downstream phases call them correctly.`,
  { label: 'impl:storage-service', effort: 'high' }
)
await reviewGate('Phase 0', 'boto3 isolated to this module; client lazy so import has no side effects; config uses pydantic-settings not os.getenv', 'app/services/object_storage_service.py, app/config.py, tests/test_object_storage_service.py, pyproject.toml')

// commit phase 0 to main so worktrees branch from it
await agent(
  `In ${REPO} on the current branch, stage and commit the Phase 0 changes (storage service, config, deps, its tests) with message "feat(r2): add object storage service + R2 config (phase 0)". Use git add -A then git commit. Report the commit hash. Do not push.`,
  { label: 'commit:phase0' }
)

// ================= PHASE 1 — parallel isolated worktrees =================
phase('Phase 1: Media paths')
await parallel([
  () =>
    agent(
      `${SPEC_CTX}\nImplement tasks group 3 (Image write & cleanup paths) from tasks.md. object_storage_service.py already exists and is committed — import and use it; do NOT modify it.\n` +
        `- Refactor app/services/image_service.py: upload the 3 WebP variants to R2 (ContentType image/webp) via object_storage_service, return R2 public URLs; remove /static/products string construction and local disk writes.\n` +
        `- app/services/product_image_service.py add_image: upload-before-DB-write ordering (no row if upload failed). Rework _unlink_image_files and _derive_thumbnail_url to delete R2 objects by key (best-effort); handle legacy /static (disk unlink) + external absolute URLs (skip).\n` +
        `- Verify app/services/about_service.py owner-image path works through the refactored image_service (R2 URLs), no separate disk logic.\n` +
        `Run .venv/bin/ruff and the image-related tests you can (.venv/bin/pytest tests/test_image.py tests/test_product_image_service.py -q) — note some may need Phase 3 test updates; report which fail and why. Touch ONLY image/about files, never video files.`,
      { label: 'impl:image-path', phase: 'Phase 1: Media paths', isolation: 'worktree', effort: 'high' }
    ),
  () =>
    agent(
      `${SPEC_CTX}\nImplement tasks group 4 (Video write & cleanup paths) from tasks.md. object_storage_service.py already exists and is committed — import and use it; do NOT modify it.\n` +
        `- Update app/services/video_service.py + app/services/product_video_service.py drain_video_transcodes: keep raw uploads staged in video_upload_temp_path and ffmpeg reading/writing local temp; after successful transcode+poster, upload MP4 (video/mp4) and poster (image/webp) to R2, set R2 public URLs, null source_path, unlink local temp outputs.\n` +
        `- On R2 upload failure: do not transition to ready; route through existing fail/cleanup path.\n` +
        `- Rework video_service.unlink_video_files to delete R2 objects for mp4/poster (best-effort) and still unlink local temp originals; confirm poster-fallback-to-primary-thumbnail still works with R2 URLs.\n` +
        `Run .venv/bin/ruff and video tests (.venv/bin/pytest tests/test_video_service.py tests/test_product_video_service.py -q) — some may need Phase 3 test updates; report failures. Touch ONLY video files, never image/about files.`,
      { label: 'impl:video-path', phase: 'Phase 1: Media paths', isolation: 'worktree', effort: 'high' }
    ),
])

// merge both worktrees back into main (disjoint file sets → trivial)
await agent(
  `Two worktree branches under ${REPO}/.claude/worktrees/ contain Phase 1 work: one edited image_service.py/product_image_service.py/about_service.py, the other video_service.py/product_video_service.py. Their file sets are disjoint. Merge BOTH branches into the current branch of the main repo at ${REPO} (git merge each worktree branch, or cherry-pick their commits). Resolve any trivial conflicts. Then run .venv/bin/ruff check . and report git status. Report any merge conflict you could not resolve.`,
  { label: 'merge:phase1', effort: 'high' }
)
await reviewGate('Phase 1', 'image and video write paths both go through object_storage_service; delete paths are best-effort and handle legacy/external URLs; no local /static writes remain for product media', 'app/services/image_service.py, app/services/product_image_service.py, app/services/video_service.py, app/services/product_video_service.py, app/services/about_service.py')

// ================= PHASE 2 — backfill + orphan fix, on main =================
phase('Phase 2: Backfill + orphan fix')
await agent(
  `${SPEC_CTX}\nImplement tasks group 5 (deactivation orphan fix) and group 7 (backfill script) in the MAIN tree at ${REPO}.\n` +
    `- product_service.deactivate_product: delete the product's image objects from R2 (best-effort, logged) alongside the existing delete_video_if_exists call.\n` +
    `- Create scripts/backfill_media_to_r2.py: iterate product_images and product_videos; for each /static/products/... URL upload the on-disk file under its derived R2 key and rewrite the DB column to the R2 public URL. Idempotent (skip rows already on public base), resumable (per-row commit), --dry-run flag, run summary (uploaded/skipped/missing counts), leave external absolute URLs untouched, log-and-continue on missing files, and write a rewrite log to support reverse-mapping on rollback.\n` +
    `Run .venv/bin/ruff on changed files.`,
  { label: 'impl:backfill-orphan', effort: 'high' }
)
await reviewGate('Phase 2', 'backfill is idempotent/resumable/dry-run correct; external URLs untouched; deactivation cleanup is best-effort and does not block deactivation', 'scripts/backfill_media_to_r2.py, app/services/product_service.py')

// ================= PHASE 3 — tests + full gate =================
phase('Phase 3: Tests + gate')
await agent(
  `${SPEC_CTX}\nImplement tasks group 8 (Tests) in the MAIN tree at ${REPO}.\n` +
    `- Wire the fake object storage backend into fixtures (tests/conftest.py and tests/realapp/conftest.py).\n` +
    `- Update tests/test_image.py, tests/test_product_image_service.py, tests/test_video_service.py, tests/test_product_video_service.py, tests/test_admin_routes.py, tests/realapp/test_about_routes.py to assert on R2 keys/URLs and storage calls instead of on-disk files.\n` +
    `- Add: deactivating a product deletes its image objects; a Layer-1 isolation test (checkout works while the storage backend raises); backfill tests (dry-run no-op, idempotent re-run, missing file non-fatal, external URLs untouched).\n` +
    `Then run the FULL suite: .venv/bin/pytest -n auto --dist worksteal -q and .venv/bin/ruff check .  Iterate until BOTH are green. Report the final pass/fail counts verbatim.`,
  { label: 'impl:tests-gate', effort: 'high' }
)
const finalReview = await reviewGate('Phase 3', 'full suite green; new code paths covered; no layer-boundary regressions across the entire diff', '')

// mark tasks.md checkboxes + summarize
await agent(
  `In ${REPO}, review the full git diff for the migrate-image-storage-to-r2 change and check off the completed items in openspec/changes/migrate-image-storage-to-r2/tasks.md by changing "- [ ]" to "- [x]" for each task that is genuinely done in the working tree. Leave the deploy/cutover tasks (group 9.2-9.5, which need a live R2 bucket) unchecked. Run 'openspec validate migrate-image-storage-to-r2'. Report which task groups are complete and which remain (and why).`,
  { label: 'finalize:tasks', effort: 'high' }
)

return {
  change: 'migrate-image-storage-to-r2',
  finalReviewVerdict: finalReview ? finalReview.verdict : 'needs_human_review',
  note: 'Phases 0-3 implemented + per-phase reviewed. Deploy/cutover (bucket provisioning, backfill run, /static retirement) require a live R2 environment and were intentionally left to a human.',
}
