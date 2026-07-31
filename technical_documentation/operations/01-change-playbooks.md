# Change Playbooks

Use these when you know what you need to change but not the blast radius.

## Add A Product Field

Touch points:

1. `app/database.py`: column and migration/backfill if persisted.
2. `app/models/products.py`: request/response/admin models.
3. `app/services/product_service.py`: create/update/list/detail mapping.
4. `app/routes/admin.py`: CSV import if admin import should support it.
5. `frontend/lib/types.ts`: mirror field.
6. `frontend/lib/api.ts` and `mock-api.ts`: response/payload shape.
7. `frontend/components/admin/ProductForm.tsx`: editing UI.
8. `frontend/components/products/*`: public display if relevant.
9. Tests: model/service/admin route/frontend form.

Watch for:

- bilingual fields need both languages
- public vs admin-only visibility
- old DB migration
- CSV import compatibility

## Add A Checkout Field

Touch points:

1. `app/models/orders.py`: request/response model.
2. `app/services/order_service.py`: transaction and persisted snapshot.
3. `app/database.py`: order column or JSON structure.
4. `frontend/lib/types.ts`: checkout/order types.
5. `frontend/app/[locale]/checkout/page.tsx`: form state and submit payload.
6. `frontend/components/checkout/*`: UI.
7. Email templates if customer/admin must see it.
8. Admin order detail if owner needs it.

Watch for:

- never trust frontend totals
- keep transaction atomic
- preserve form input on error
- include field in order detail/history if needed

## Add A New Admin Page

Touch points:

1. Backend route/service/model if data is new.
2. `frontend/app/[locale]/admin/<page>/page.tsx`.
3. `frontend/components/admin/AdminSidebar.tsx`.
4. `frontend/contexts/AdminContext.tsx` only if shared admin state changes.
5. `frontend/messages/en.json` and `bg.json`.
6. Tests for page behavior and backend access.

Watch for:

- backend admin auth is required
- frontend guard is not enough
- loading, empty, error states

## Add A Public Content Page

Touch points:

1. `frontend/app/[locale]/<page>/page.tsx`.
2. Header/footer navigation if discoverable.
3. SEO metadata/alternate links if needed.
4. Translations in both message files.
5. Backend content service if admin-managed.
6. Tests for page rendering.

Watch for:

- no hardcoded user-visible strings
- legal/contact pages need privacy links/copy

## Add A Webhook

Touch points:

1. `app/routes/webhooks.py` or new router.
2. `app/config.py`: signing secret.
3. `session_skip_paths` in settings.
4. Service handler for verified payload.
5. Tests for bad signature, valid signature, duplicate delivery if relevant.

Rules:

- verify raw body before trusting payload
- cap body size
- do not create session cookies for webhooks
- avoid raw payload logging

## Add A Background Job

First ask if it fits an existing loop:

- cleanup: `cleanup_runtime_records`
- email: outbox pattern
- media: video transcode loop

If new loop is truly needed:

1. Add durable DB state first.
2. Make work idempotent.
3. Catch/log exceptions inside loop.
4. Add task to lifespan startup/shutdown.
5. Test task body without waiting real time.

## Add A New Status

Touch points:

1. Backend `Literal` type.
2. Database CHECK constraint or migration.
3. Service state machine.
4. Admin/customer labels.
5. Frontend status badge/timeline maps.
6. Tests for transitions and display.

Watch for:

- payment status and order status are separate
- email behavior may depend on status
- dashboard metrics may need filtering changes

