## Context

Atelier Marie currently has FAQ, contact, checkout, footer, and bilingual routing, but no dedicated legal-policy page. Returns are already mentioned in FAQ seed content, yet the customer-facing source of truth does not exist. The store is Bulgaria-based and sells physical handmade candles to consumers, so the UI needs clear pre-purchase information about seller terms, delivery, withdrawal, returns, custom products, faulty goods, and refunds.

The product decision is intentionally conservative: cover the legal minimum clearly without presenting returns as a sales benefit.

## Goals / Non-Goals

**Goals:**
- Provide a localized `/terms` page with quiet, premium presentation.
- Include a clear `#returns` section that covers the 14-day withdrawal flow and manual request process.
- Surface Terms & Conditions before purchase through checkout text.
- Add footer discoverability without adding a standalone Returns footer item.
- Keep the implementation static and frontend-only for MVP.

**Non-Goals:**
- No return portal or upload flow.
- No return database tables, return statuses, or admin return workflow.
- No automatic refunds or payment-provider refund integration.
- No claim that returns are free or easy as a marketing promise.
- No reliance on the hygiene-seal exception, because candles ship in packaging but not with a real hygiene/safety seal.

## Decisions

### 1. Single Terms & Conditions page, not a standalone Returns page

Use `/[locale]/terms` as the legal source of truth. Returns live under `#returns` inside that page.

Rationale: this keeps returns compliant and findable while avoiding a promotional returns page. The footer stays calm: Terms & Conditions, FAQ, Contact, social links.

Alternative considered: `/returns` page. Rejected because it over-emphasizes returns relative to the owner's stated preference.

### 2. Static localized frontend content

Terms content lives in `frontend/messages/en.json` and `frontend/messages/bg.json` and renders through a new server page.

Rationale: the content is stable legal chrome, not frequently edited store content. This avoids new database tables and admin UI. It also matches existing page chrome localization patterns.

Alternative considered: admin-managed terms. Rejected for MVP because legal text should be controlled and reviewed, not casually edited.

### 3. Open, scannable legal layout

Render all sections as readable content, with a compact section navigation at the top. Do not hide the legal text inside accordion-only UI.

Rationale: legal information must be clear before purchase. A narrow text column, section anchors, and restrained styling make the page beautiful without making information hard to find.

Alternative considered: accordion terms. Rejected because hidden legal sections are worse for scanning and compliance.

### 4. Manual return request process

Customers request withdrawal or return support through email/contact form. The page states that any clear withdrawal statement is sufficient and includes the model withdrawal form text.

Rationale: EU withdrawal cannot depend on discretionary approval. The business can still reply with return address/instructions manually.

Alternative considered: self-service return portal with photo upload. Rejected until return volume justifies it.

### 5. Photos only for damaged, faulty, or wrong items

The policy requests photos for damaged/faulty/incorrect items, but not for normal withdrawal.

Rationale: photos are operationally useful for problem cases, but requiring them for ordinary withdrawal adds friction to a statutory right.

## Risks / Trade-offs

- **Legal text may need jurisdiction-specific review** -> Keep the page editable in code and add a concise disclaimer in handoff/final notes that legal review is still required.
- **Static text requires deployment for edits** -> Accept for MVP; terms changes should be deliberate.
- **FAQ answer may still be admin-managed in existing DB** -> Do not rely on FAQ as the legal source of truth; footer and checkout link directly to `/terms`.
- **Manual return handling has no audit trail** -> Accept until return volume justifies a `returns` entity and admin workflow.
