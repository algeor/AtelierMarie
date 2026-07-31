## 1. Legal Identity and Policy Pages

- [x] 1.1 Add a centralized frontend legal identity source with public trader/controller fields, responsible-party fields, contact email, policy path helpers, and explicit placeholders for owner-supplied legal values that must be reviewed before launch.
- [x] 1.2 Add localized Privacy Policy message content in `frontend/messages/en.json` and `frontend/messages/bg.json` covering current data categories, purposes/legal bases, recipients/processors, retention references, rights, and privacy contact details.
- [x] 1.3 Add localized Cookie Policy message content listing current session/auth/locale cookies, purpose, type, duration where known, and a no-nonessential-tracking statement for the current app.
- [x] 1.4 Create localized `/[locale]/privacy` and `/[locale]/cookies` pages with metadata, alternate links, readable legal layout, and content sourced from localized messages and legal identity helpers.
- [x] 1.5 Expand existing Terms & Conditions content with centralized trader identity, legal contact, price/tax/payment wording, and links to Privacy and Cookie policies.
- [x] 1.6 Add privacy and cookie policy static routes to `frontend/app/sitemap.ts` with localized alternates.

## 2. Storefront Legal Discoverability and Disclosures

- [x] 2.1 Update the footer to include localized Privacy Policy and Cookie Policy links while keeping Terms & Conditions and avoiding standalone Returns or obsolete ODR links.
- [x] 2.2 Add a concise privacy notice and localized Privacy Policy link near the contact form submit button.
- [x] 2.3 Update checkout legal disclosure near every Place Order button to link to Terms & Conditions and Privacy Policy and mention processing of contact/delivery data.
- [x] 2.4 Fix checkout order summary to use `effective_price_cents` for discounted line totals and subtotal display.
- [x] 2.5 Add checkout shipping/total clarity so known shipping is shown as a row and unknown/unimplemented paid delivery is not implied as included.
- [x] 2.6 Update order confirmation UI to show subtotal, shipping, total, and localized Terms/Privacy links after successful order placement.

## 3. Email Legal References

- [x] 3.1 Extend the email rendering context with localized public URLs for Terms, Privacy, Cookies, and Contact plus centralized legal identity/trader contact values.
- [x] 3.2 Update English order placed and payment-pending email templates with concise Terms, withdrawal/returns, Privacy, and trader contact references.
- [x] 3.3 Update Bulgarian order placed and payment-pending email templates with equivalent localized legal references.
- [x] 3.4 Add or update email renderer tests proving legal URLs/contact references render in both locales without removing existing order summary/payment content.

## 4. Product Safety Backend and API

- [x] 4.1 Add nullable/default-safe product safety columns to `app/database.py` for localized safety warnings and care instructions, including migration/backfill support for existing databases.
- [x] 4.2 Add product safety fields and validation bounds to Pydantic create/update/admin/public product models.
- [x] 4.3 Update product service create/update/list/detail mappings so safety metadata is persisted, preserved on partial update, and locale-resolved for public responses.
- [x] 4.4 Update admin CSV import parsing and validation to accept optional safety warning and care instruction columns.
- [x] 4.5 Update frontend product/admin TypeScript types and mock API fixtures/handlers for the new safety metadata fields.

## 5. Product Safety UI

- [x] 5.1 Add localized admin product form controls for English/Bulgarian safety warnings and care instructions, with validation and submit payload coverage.
- [x] 5.2 Add localized storefront product detail rendering for safety warnings, care/use instructions, product identifier, and responsible-party/trader information.
- [x] 5.3 Ensure product safety sections are responsive, accessible, and hidden only when optional product-specific safety text is absent while responsible-party information remains discoverable.
- [x] 5.4 Add i18n labels/help text for product safety fields and product detail safety sections in English and Bulgarian.

## 6. FAQ and Existing Content Cleanup

- [x] 6.1 Update seeded FAQ returns wording to point to Terms & Conditions instead of a non-existent Returns & Refunds Policy.
- [x] 6.2 Add a conservative marker-guarded migration that updates only the exact old seeded FAQ returns answer on existing databases, preserving owner-edited FAQ text.
- [x] 6.3 Verify no storefront/footer/legal text links to a missing standalone returns page or outdated ODR platform.

## 7. Tests and Validation

- [x] 7.1 Add backend tests for product safety model validation, admin create/update round trip, public product response locale fallback, and CSV import safety columns.
- [x] 7.2 Add backend migration/FAQ tests proving existing products survive safety-column migration and exact old FAQ returns text is updated once.
- [x] 7.3 Add frontend tests for Privacy/Cookie page rendering, footer legal links, contact privacy notice, checkout legal disclosure/price summary, order confirmation policy links, admin safety fields, and product detail safety section.
- [x] 7.4 Run `openspec validate legal-compliance-foundation --strict` and fix any artifact issues.
- [x] 7.5 Run focused backend and frontend tests touched by this change, then run broader frontend/backend checks if the focused changes pass.
- [x] 7.6 Document remaining owner/legal-review inputs in the final implementation notes, especially legal identity, VAT/tax wording, delivery-charge treatment, and target-country assumptions.
