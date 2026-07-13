# Admin Panel Expansion — Exploration

## Vision

A single, comprehensive admin UI where the shop owner can manage the entire business:
orders, products, comments, and customer communication — without touching code or a database.

---

## Current State

```
┌─────────────────────────────────────────────────────────────────────────┐
│  WHAT EXISTS TODAY                                                        │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  /admin                  Dashboard (stats cards)                           │
│  /admin/products         Product list (paginated, activate/deactivate)    │
│  /admin/products/new     Create product form (+ image upload)             │
│  /admin/products/[id]    Edit product form (+ image upload)               │
│  /admin/orders           Order list (status filter, status change)         │
│                                                                           │
│  Backend APIs exist but have NO frontend page:                            │
│    GET  /v1/admin/comments       (list all for moderation)                │
│    DELETE /v1/admin/comments/:id  (hard-delete)                           │
│                                                                           │
│  NOT implemented at all:                                                  │
│    Email system (transactional or marketing)                              │
│    Order editing (line items, address, notes)                             │
│    Tracking numbers / carrier info                                        │
│    Product deprecation lifecycle                                          │
│    Product size/volume as a first-class attribute                          │
│    Promo email broadcasts                                                 │
│    Subscriber/mailing list management                                     │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Proposed Admin Navigation Structure

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ADMIN SIDEBAR                                                            │
│                                                                           │
│  ┌─────────────────────┐     ┌────────────────────────────────────────┐  │
│  │                     │     │                                        │  │
│  │  📊 Dashboard       │     │   MAIN CONTENT AREA                    │  │
│  │                     │     │                                        │  │
│  │  📦 Products        │     │                                        │  │
│  │    • All Products   │     │                                        │  │
│  │    • Add New        │     │                                        │  │
│  │    • Categories     │     │                                        │  │
│  │                     │     │                                        │  │
│  │  🛒 Orders          │     │                                        │  │
│  │    • All Orders     │     │                                        │  │
│  │    • Pending        │     │                                        │  │
│  │    • Shipped        │     │                                        │  │
│  │                     │     │                                        │  │
│  │  💬 Comments        │     │                                        │  │
│  │    • Moderation     │     │                                        │  │
│  │                     │     │                                        │  │
│  │  ✉️  Email           │     │                                        │  │
│  │    • Templates      │     │                                        │  │
│  │    • Send Promo     │     │                                        │  │
│  │    • Subscribers    │     │                                        │  │
│  │                     │     │                                        │  │
│  │  ← Back to Store   │     │                                        │  │
│  │                     │     │                                        │  │
│  └─────────────────────┘     └────────────────────────────────────────┘  │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Feature Breakdown

### 1. Order Management (Enhanced)

#### 1A. Order Tracking

**What exists:** Status change dropdown (pending → confirmed → shipped → delivered / cancelled).

**What's needed:**
- When transitioning to "shipped", expand a form:
  - Tracking number (required)
  - Carrier dropdown (Speedy, Econt, DHL, FedEx, Other)
  - Tracking URL (auto-generated from carrier + number, or manual override)
- Order detail view showing full timeline with tracking info
- Customer-facing tracking display on their order page

**Schema change required:**
```sql
ALTER TABLE orders ADD COLUMN tracking_number TEXT;
ALTER TABLE orders ADD COLUMN tracking_carrier TEXT;
ALTER TABLE orders ADD COLUMN tracking_url TEXT;
```

**Carrier auto-URL patterns:**
| Carrier | URL Template |
|---------|-------------|
| Speedy  | `https://www.speedy.bg/en/track-shipment?shipmentNumber={num}` |
| Econt   | `https://www.econt.com/services/track-shipment/{num}` |
| DHL     | `https://www.dhl.com/en/express/tracking.html?AWB={num}` |
| FedEx   | `https://www.fedex.com/fedextrack/?trknbr={num}` |

```
┌─────────────────────────── Order Detail View ───────────────────────────┐
│                                                                          │
│  Order #abc-123            Status: [Shipped ▼]                           │
│  ──────────────────────────────────────────────────                      │
│                                                                          │
│  Customer: A***@gmail.com                                                │
│  Name: Maria Georgieva                                                   │
│  Address: ul. Tsar Boris III 42, Sofia 1000                              │
│  Notes: "Please wrap as gift"                                            │
│                                                                          │
│  ┌─────────────────── Timeline ──────────────────────┐                   │
│  │  ● Placed       2026-07-10 14:32                  │                   │
│  │  ● Confirmed    2026-07-10 15:01                  │                   │
│  │  ● Shipped      2026-07-11 09:45                  │                   │
│  │    Carrier: Speedy                                │                   │
│  │    Tracking: 1234567890                           │                   │
│  │    Link: speedy.bg/track/1234567890               │                   │
│  │  ○ Delivered    (pending)                         │                   │
│  └───────────────────────────────────────────────────┘                   │
│                                                                          │
│  ┌─────────────────── Items ─────────────────────────┐                   │
│  │  Lavender Dream 300ml    × 2    €24.00            │                   │
│  │  Rose Garden 500ml       × 1    €18.00            │                   │
│  │                                  ─────            │                   │
│  │                         Total:   €66.00           │                   │
│  └───────────────────────────────────────────────────┘                   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

#### 1B. Order Editing

**Spectrum of "editing":**

| Level | What can change | Complexity | Recommendation |
|-------|----------------|-----------|---------------|
| Notes only | Admin internal notes (not visible to customer) | Low | ✅ Start here |
| Contact info | Shipping address, customer name | Medium | ✅ Useful |
| Status + tracking | Already planned above | Medium | ✅ Planned |
| Line items | Add/remove products, change quantities | High | ⚠️ Risky — recalculates totals, breaks snapshot |
| Price override | Manual discount/adjustment | High | ⚠️ Accounting implications |

**Recommended approach — "Admin Notes + Contact Correction":**

```sql
ALTER TABLE orders ADD COLUMN admin_notes TEXT;
-- shipping_address and customer_name already exist and can be updated
```

The admin can:
- Add internal notes (e.g., "Customer called to change delivery date")
- Correct shipping address (customer typo, moved, etc.)
- Correct customer name
- View full order history with all modifications logged

**NOT recommended (for now):** Editing line items. The `order_items` table is an immutable snapshot
of what was purchased at what price. Modifying it opens a can of worms:
- Do you refund the difference?
- What about stock adjustments?
- Audit trail breaks

If you need to "fix" an order, the better UX is: cancel + re-create.

---

### 2. Product Management (Enhanced)

#### 2A. What Already Works

The ProductForm already supports:
- Name (EN + BG bilingual)
- Description (EN + BG bilingual)
- Category (dropdown)
- Price (EUR → stored as cents)
- Stock quantity
- Image upload (JPEG/PNG → WebP)
- Materials
- Days to craft
- Featured toggle

#### 2B. Size / Volume — New Attribute

Products currently encode size in the slug (`lavender-dream-300ml`) but there's no queryable `size` field.

**Option A: Simple size text field**
```sql
ALTER TABLE products ADD COLUMN size TEXT;  -- "300ml", "500ml", "Set of 3"
```
Pros: Simple, flexible, immediate
Cons: No structured filtering, just display text

**Option B: Size as structured data**
```sql
ALTER TABLE products ADD COLUMN volume_ml INTEGER;
ALTER TABLE products ADD COLUMN weight_g INTEGER;
```
Pros: Filterable ("show all 300ml candles"), sortable
Cons: Not all products have volume (gift sets, accessories)

**Option C: Product variants (parent + children)**
```
Product "Lavender Dream"
  ├── Variant: 300ml — €12.00
  └── Variant: 500ml — €18.00
```
Pros: Proper e-commerce pattern, shared description/images
Cons: Major refactor — affects cart, checkout, orders, search. Overkill for <50 products.

**Recommendation:** Option A (text field) now, Option B later if filtering is needed.
At <50 products, the catalog is small enough to browse without structured size filters.

#### 2C. Product Deprecation / Lifecycle

Current state: binary `is_active` (1 = visible + purchasable, 0 = hidden).

**Proposed lifecycle:**

```
                    ┌──────────────────────────────────────────────┐
                    │         PRODUCT LIFECYCLE                      │
                    │                                                │
  ┌─────────┐      │  ┌────────┐    ┌────────────┐    ┌─────────┐ │
  │  Draft   │─────▶│  │ Active │───▶│ Deprecated │───▶│Archived │ │
  │(new,not  │      │  │        │    │            │    │         │ │
  │published)│      │  │Visible │    │Visible but │    │Hidden   │ │
  └─────────┘      │  │Buyable │    │NOT buyable │    │entirely │ │
                    │  │        │    │"End of     │    │         │ │
                    │  │        │    │ line" badge│    │         │ │
                    │  └────────┘    └────────────┘    └─────────┘ │
                    │       ▲                                │      │
                    │       │         (re-activate)          │      │
                    │       └────────────────────────────────┘      │
                    │                                                │
                    └──────────────────────────────────────────────┘
```

**Schema:**
```sql
-- Replace is_active INTEGER with:
ALTER TABLE products ADD COLUMN status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('draft', 'active', 'deprecated', 'archived'));
-- Migration: is_active=1 → 'active', is_active=0 → 'archived'
```

**UI implications:**
- Product list shows status badge (color-coded)
- "Deprecate" button on active products → shows "End of line" on storefront
- "Archive" button on deprecated products → hides entirely
- "Re-activate" button on archived/deprecated → back to active
- Draft status for products being prepared but not yet published

**Storefront behavior:**
| Status | Visible in catalog? | Can add to cart? | Detail page accessible? |
|--------|:------------------:|:----------------:|:----------------------:|
| Draft | ❌ | ❌ | ❌ |
| Active | ✅ | ✅ | ✅ |
| Deprecated | ✅ (with badge) | ❌ | ✅ |
| Archived | ❌ | ❌ | ❌ (404) |

#### 2D. Product Form Enhancements

Add to the existing ProductForm:
- **Size field** (free text, e.g., "300ml", "500ml", "Gift Set")
- **Status dropdown** (Draft / Active / Deprecated / Archived)
- **SEO slug preview** (show what the URL will look like)
- Existing fields already cover: name, description, price, stock, image, materials, category

---

### 3. Comment Moderation Page

**Backend already supports:**
- `GET /v1/admin/comments?page=1&limit=20&product_id=xyz` — list all comments
- `DELETE /v1/admin/comments/{id}` — hard-delete

**Frontend page needed:**

```
┌───────────────────────── Comment Moderation ────────────────────────────┐
│                                                                          │
│  Filter: [All Products ▼]   Search: [____________]   Sort: [Newest ▼]   │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  💬 "Love this candle! The lavender scent is heavenly"            │  │
│  │  ──────────────────────────────────────────────────────            │  │
│  │  Product: Lavender Dream 300ml                                     │  │
│  │  Session: a3f2...b891  •  2026-07-12 14:32                        │  │
│  │                                                                    │  │
│  │  [🗑️ Delete]  [👁️ View on product page]                            │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  💬 "Shipping was slow but quality is great"                       │  │
│  │  ──────────────────────────────────────────                        │  │
│  │  Product: Rose Garden 500ml                                        │  │
│  │  Session: f1e9...c234  •  2026-07-11 09:15                        │  │
│  │                                                                    │  │
│  │  [🗑️ Delete]  [👁️ View on product page]                            │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ◀ 1 2 3 ▶                                                              │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Possible enhancements (beyond MVP):**
- "Hide" action (soft-delete — keeps record, hides from public) vs. current hard-delete only
- Bulk select + delete
- Auto-flag comments with certain keywords
- Reply from admin (appears as "Shop Owner" response)

---

### 4. Email System

This is the biggest new capability and breaks into three sub-systems:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EMAIL ARCHITECTURE                                │
│                                                                           │
│  ┌────────────────────┐  ┌────────────────────┐  ┌──────────────────┐   │
│  │  A. Transactional   │  │  B. Template        │  │  C. Marketing    │   │
│  │     Emails          │  │     Editor          │  │     Broadcasts   │   │
│  ├────────────────────┤  ├────────────────────┤  ├──────────────────┤   │
│  │                    │  │                    │  │                  │   │
│  │ Triggered by       │  │ Admin edits email  │  │ Compose + send   │   │
│  │ order events:      │  │ templates:         │  │ to all/some      │   │
│  │                    │  │                    │  │ subscribers:     │   │
│  │ • Order placed     │  │ • Subject line     │  │                  │   │
│  │ • Order confirmed  │  │ • Body text        │  │ • Promo emails   │   │
│  │ • Order shipped    │  │ • Variables        │  │ • New product    │   │
│  │ • Order delivered  │  │   ({{name}},       │  │   announcements  │   │
│  │ • Order cancelled  │  │    {{order_id}})   │  │ • Seasonal       │   │
│  │                    │  │ • Preview          │  │   campaigns      │   │
│  │ Provider: Resend   │  │ • EN + BG          │  │                  │   │
│  │ Mode: fire & forget│  │                    │  │ Requires:        │   │
│  │                    │  │ Storage: DB or     │  │ • Subscriber     │   │
│  │                    │  │ file templates     │  │   list mgmt      │   │
│  └────────────────────┘  └────────────────────┘  │ • Unsubscribe    │   │
│                                                   │ • GDPR consent   │   │
│         Spec exists:                              │ • Batch send     │   │
│         openspec/changes/email-notifications/     └──────────────────┘   │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 4A. Transactional Emails (Already Specced)

The `email-notifications` proposal covers this fully. Summary:
- Provider: Resend (100/day free, modern API)
- Trigger: BackgroundTasks after order state change
- Templates: Jinja2 plain text (EN + BG), HTML later
- Failure: fire-and-forget, log errors, never block orders
- Prerequisite: Domain registration + DNS (SPF/DKIM/DMARC)

#### 4B. Template Editor (Admin UI for Editing Emails)

**Options:**

| Approach | Complexity | Flexibility |
|----------|:----------:|:-----------:|
| File-based templates, edit in admin as plain text/markdown | Medium | High |
| DB-stored templates with variable interpolation | Medium-High | High |
| Rich drag-and-drop email builder | Very High | Very High |
| Pre-built templates, admin only tweaks header/footer/promo banner | Low | Limited |

**Recommended: DB-stored templates with plain text + variable preview**

```
┌─────────────────── Email Template Editor ──────────────────────────────┐
│                                                                         │
│  Template: [Order Confirmation ▼]    Language: [🇬🇧 EN] [🇧🇬 BG]        │
│                                                                         │
│  Subject: ─────────────────────────────────────────────────────         │
│  │ Your Atelier Marie Order #{{order_id_short}} ✨                │     │
│  ──────────────────────────────────────────────────────────────         │
│                                                                         │
│  Body: ────────────────────────────────────────────────────────         │
│  │ Hi {{customer_name}},                                          │     │
│  │                                                                │     │
│  │ Thank you for your order! Here's what you ordered:             │     │
│  │                                                                │     │
│  │ {{#each items}}                                                │     │
│  │ - {{product_name}} × {{quantity}} — {{price_display}}          │     │
│  │ {{/each}}                                                      │     │
│  │                                                                │     │
│  │ Total: {{total_display}}                                       │     │
│  │                                                                │     │
│  │ With love,                                                     │     │
│  │ Atelier Marie 🕯️                                               │     │
│  ──────────────────────────────────────────────────────────────         │
│                                                                         │
│  Available variables:                                                    │
│  {{customer_name}} {{order_id}} {{order_id_short}} {{total_display}}    │
│  {{items}} {{tracking_number}} {{tracking_url}} {{carrier}}             │
│                                                                         │
│  [Preview with sample data]    [Save]    [Reset to default]             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Schema:**
```sql
CREATE TABLE email_templates (
    id          TEXT PRIMARY KEY,    -- 'order_placed', 'order_shipped', etc.
    locale      TEXT NOT NULL,       -- 'en', 'bg'
    subject     TEXT NOT NULL,
    body        TEXT NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_by  TEXT REFERENCES users(id),
    UNIQUE(id, locale)
);
```

On startup, seed with default templates from files. Admin edits save to DB.
Email service checks DB first, falls back to file templates if row missing.

#### 4C. Marketing / Promo Emails (Broadcast)

This is the most complex addition because it introduces new concepts:

**1. Subscriber Management**

Who gets promo emails? Options:
- **All users who placed an order** (implicit consent via purchase — check GDPR)
- **Explicit opt-in** (checkbox at checkout: "Send me news about new candles")
- **Separate newsletter signup** (form on homepage/footer)

```sql
CREATE TABLE subscribers (
    id          TEXT PRIMARY KEY,
    email       TEXT UNIQUE NOT NULL,
    name        TEXT,
    locale      TEXT NOT NULL DEFAULT 'en',
    source      TEXT NOT NULL,  -- 'checkout', 'signup_form', 'admin_import'
    is_active   INTEGER NOT NULL DEFAULT 1,
    subscribed_at TEXT NOT NULL DEFAULT (datetime('now')),
    unsubscribed_at TEXT
);
```

**2. Campaign Compose UI**

```
┌─────────────────── Send Promo Email ───────────────────────────────────┐
│                                                                         │
│  Campaign Name: [Summer Sale 2026_____________]                         │
│                                                                         │
│  Recipients: [All active subscribers (47)] ▼                            │
│              • All subscribers                                           │
│              • Only EN subscribers                                       │
│              • Only BG subscribers                                       │
│              • Custom segment                                            │
│                                                                         │
│  Subject: [🌸 Summer Sale — 20% off all candles!___]                   │
│                                                                         │
│  Body: ────────────────────────────────────────────────────────         │
│  │ Hi {{name}},                                                   │     │
│  │                                                                │     │
│  │ Summer is here and we're celebrating with 20% off              │     │
│  │ our entire collection!                                         │     │
│  │                                                                │     │
│  │ Use code SUMMER20 at checkout.                                 │     │
│  │ Valid until July 31, 2026.                                     │     │
│  │                                                                │     │
│  │ Shop now: {{shop_url}}                                         │     │
│  │                                                                │     │
│  │ With love,                                                     │     │
│  │ Marie 🕯️                                                       │     │
│  ──────────────────────────────────────────────────────────────         │
│                                                                         │
│  ⚠️  This will send to 47 subscribers.                                  │
│  Each email includes an unsubscribe link (required by law).             │
│                                                                         │
│  [Preview]  [Send Test to Me]  [📤 Send Campaign]                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**3. Legal Requirements (GDPR/E-Privacy)**

Bulgarian law follows EU GDPR:
- Unsubscribe link in EVERY marketing email (one-click)
- Clear consent record (when, how, what they agreed to)
- Cannot email without consent (purchase alone may not be enough for marketing)
- Unsubscribe endpoint: `GET /unsubscribe?token=...` (signed token, no login needed)

**4. Sending Strategy**

At this scale (<100 subscribers), Resend's free tier (100/day) handles it:
- Batch send via Resend's batch API
- Or loop + send with small delay (avoid rate limits)
- Log each send (success/bounce)
- Track campaign stats (sent, opened — Resend provides this)

```sql
CREATE TABLE campaigns (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    subject     TEXT NOT NULL,
    body        TEXT NOT NULL,
    locale      TEXT,            -- NULL = all locales
    status      TEXT NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft', 'sending', 'sent', 'failed')),
    sent_count  INTEGER DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    sent_at     TEXT
);

CREATE TABLE campaign_sends (
    id          TEXT PRIMARY KEY,
    campaign_id TEXT REFERENCES campaigns(id),
    subscriber_id TEXT REFERENCES subscribers(id),
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'sent', 'bounced', 'failed')),
    sent_at     TEXT
);
```

---

### 5. Image Upload (Already Complete)

**Fully working today:**
- ProductForm has file input (JPEG/PNG, ≤5MB)
- Backend: validates magic bytes, strips EXIF, converts to WebP
- Generates main (1200×1500) + thumbnail (400×500)
- Returns `{ image_url, thumbnail_url }`
- Path traversal protection, pixel flood protection (25MP max)

**No changes needed** unless you want:
- Multiple images per product (gallery) — currently single image
- Drag-and-drop upload UX improvement
- Image cropping/positioning UI

---

## Implementation Priority & Dependencies

```
┌─────────────────────────────────────────────────────────────────────────┐
│  DEPENDENCY GRAPH                                                         │
│                                                                           │
│  Phase 1 (Quick Wins — Backend exists)                                    │
│  ─────────────────────────────────────                                    │
│  ┌───────────────────┐  ┌────────────────────┐                           │
│  │ Comments           │  │ Order Detail View   │                          │
│  │ Moderation Page    │  │ (expanded, timeline)│                          │
│  │ (frontend only)    │  │ + Admin Notes       │                          │
│  └───────────────────┘  └────────────────────┘                           │
│                                                                           │
│  Phase 2 (Schema Changes + New Backend)                                   │
│  ──────────────────────────────────────                                   │
│  ┌───────────────────┐  ┌────────────────────┐  ┌─────────────────────┐ │
│  │ Product Lifecycle  │  │ Order Tracking      │  │ Size Field          │ │
│  │ (deprecation      │  │ (carrier, number,   │  │ (new column,        │ │
│  │  workflow)         │  │  URL on ship)       │  │  form field)        │ │
│  └───────────────────┘  └────────────────────┘  └─────────────────────┘ │
│          │                        │                                       │
│          │                        ▼                                       │
│  Phase 3 (Email Foundation)       │                                       │
│  ──────────────────────────       │                                       │
│  ┌───────────────────────────────────────┐                                │
│  │ Email Service (Resend provider,       │                                │
│  │ Jinja2 templates, fire-and-forget,    │                                │
│  │ console mode for dev)                 │                                │
│  └───────────────────┬───────────────────┘                                │
│                      │                                                    │
│                      ▼                                                    │
│  Phase 4 (Email Admin UI)                                                 │
│  ────────────────────────                                                 │
│  ┌───────────────────────┐  ┌────────────────────────────┐               │
│  │ Template Editor        │  │ Promo/Broadcast Compose    │               │
│  │ (view/edit templates,  │  │ (subscriber list,          │               │
│  │  preview, per-locale)  │  │  compose, send, track)     │               │
│  └───────────────────────┘  └────────────────────────────┘               │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Open Questions

| # | Question | Options | Impact |
|---|----------|---------|--------|
| 1 | Should "deprecated" products still be visible on the store with a badge, or just not purchasable? | Visible with badge / Hidden entirely / Owner's choice per product | Storefront UX |
| 2 | Order editing: how far should it go? | Notes only / Notes + address / Full line-item editing | Backend complexity |
| 3 | Email templates: plain text first or jump to HTML? | Plain text → HTML later / HTML from day one / Both side by side | Time to ship |
| 4 | Promo emails: explicit opt-in at checkout, or all purchasers? | Checkbox at checkout / Separate signup / Both | Legal, conversion |
| 5 | Multiple images per product? | Single (current) / Gallery (3-5 images) | Schema + UI complexity |
| 6 | Comment moderation: hard-delete only, or add "hide" (soft-delete)? | Hard-delete / Hide + delete / Hide only | Backend change needed |
| 7 | Do you need discount codes / coupons to go with promo emails? | Yes (new feature) / No (just info emails) / Later | Large feature if yes |
| 8 | Product size: text field or structured (volume_ml + weight_g)? | Free text / Structured / Both | Filtering capability |

---

## Estimated Effort

| Feature | Backend | Frontend | Total |
|---------|:-------:|:--------:|:-----:|
| Comments moderation page | — (done) | 1 day | 1 day |
| Order detail + notes | 0.5 day | 1 day | 1.5 days |
| Order tracking (carrier/number) | 1 day | 1 day | 2 days |
| Product size field | 0.5 day | 0.5 day | 1 day |
| Product lifecycle/deprecation | 1 day | 1 day | 2 days |
| Email service foundation | 2 days | — | 2 days |
| Transactional email triggers | 1 day | — | 1 day |
| Email template editor UI | 1 day | 2 days | 3 days |
| Subscriber management | 1 day | 1 day | 2 days |
| Promo email compose + send | 1 day | 2 days | 3 days |
| Sidebar nav expansion | — | 0.5 day | 0.5 day |
| **TOTAL** | | | **~19 days** |

---

## Risk Factors

| Risk | Mitigation |
|------|-----------|
| Domain not registered yet → emails can't actually send | Console provider for dev; deploy when domain ready |
| GDPR compliance for marketing emails | Explicit opt-in, one-click unsubscribe, consent records |
| Resend free tier (100/day) may not cover promo blasts to 50+ subscribers | At current scale it's fine; upgrade to paid ($20/mo) if needed |
| Product lifecycle change touches storefront queries | Feature-flag the new status values; migrate is_active → status column |
| Order editing creates audit trail questions | Log all modifications with timestamp + who changed it |

---

## Summary

You're asking for **6 distinct features** bundled under "admin UI expansion":

1. **Order tracking + detail view** — medium effort, high value
2. **Order editing (notes + address)** — low effort, moderate value
3. **Comment moderation page** — low effort, frontend only
4. **Product lifecycle (deprecation)** — medium effort, good UX improvement
5. **Product size field** — trivial
6. **Email system (transactional + templates + broadcasts)** — largest piece, multiple phases

The good news: your backend already covers ~60% of what's needed for items 1-4. The email system is the genuinely new infrastructure. Everything else is mostly frontend pages wiring into existing APIs.

---

*This is an exploration document — no code has been written. Ready to be decomposed into change proposals when decisions are made on the open questions above.*
