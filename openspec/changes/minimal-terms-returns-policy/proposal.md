## Why

Atelier Marie needs clear EU/Bulgaria consumer-law information before purchase, but the store should not advertise returns as a marketing feature. A single quiet Terms & Conditions page can cover delivery, withdrawal, returns, custom products, faulty goods, and refunds without adding a returns portal or operational complexity.

## What Changes

- Add a localized public `/[locale]/terms` page with an elegant legal layout and section anchors, including `/terms#returns`.
- Put the statutory withdrawal and returns information inside the Terms & Conditions page, not on a standalone promotional returns page.
- Add a footer link to Terms & Conditions.
- Add a small checkout disclosure linking to Terms & Conditions before order submission.
- Keep FAQ/product-facing returns references quiet; where returns are referenced, use Terms & Conditions as the source of truth.
- Keep return handling manual: customers request returns through email/contact form; no return portal, no admin return workflow, no refund automation.
- Capture the policy decisions from exploration:
  - Standard products: 14-day statutory withdrawal.
  - Customer pays direct return shipping for change-of-mind withdrawal when disclosed.
  - Photos are required only for damaged, faulty, or incorrect items.
  - Original packaging is requested where possible, but not an absolute condition of withdrawal.
  - Lit/over-handled candles may result in diminished-value deduction.
  - Custom or clearly personalized products are excluded from withdrawal where legally permitted.
  - Faulty/damaged/wrong items remain covered by separate statutory rights.

## Capabilities

### New Capabilities
- `terms-policy-page`: Public localized Terms & Conditions page, legal-policy content structure, section anchors, metadata, and quiet premium presentation.

### Modified Capabilities
- `global-layout`: Footer includes a localized Terms & Conditions link without turning returns into a promotional footer item.
- `checkout-ui`: Checkout displays a small pre-purchase legal disclosure linking to Terms & Conditions.

## Impact

- **Frontend:** new `/[locale]/terms` page, localized strings in `messages/en.json` and `messages/bg.json`, footer link, checkout disclosure, FAQ/product link adjustments where applicable.
- **Backend:** no new public API, no schema changes, no return-management service.
- **Operations:** return requests remain manual through email/contact form; owner handles instructions, inspection, and refunds outside the app for now.
- **Compliance:** page content is informational and should still be reviewed by a qualified legal professional before launch.
