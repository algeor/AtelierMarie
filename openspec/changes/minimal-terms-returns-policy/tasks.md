## 1. Terms Page Content and Route

- [x] 1.1 Add localized `terms` message content in `frontend/messages/en.json` and `frontend/messages/bg.json`, including page metadata, section nav labels, legal sections, returns text, custom-products exception, faulty-item photo guidance, and model withdrawal form text.
- [x] 1.2 Create the localized `/[locale]/terms` page with metadata, alternate links, section navigation, readable legal layout, and the `#returns` anchor.

## 2. Discoverability and Checkout Disclosure

- [x] 2.1 Add a localized Terms & Conditions link to the footer without adding a separate Returns footer link.
- [x] 2.2 Add the small localized checkout legal disclosure near both mobile and desktop Place Order buttons, linking to `/terms`.

## 3. Tests and Validation

- [x] 3.1 Add/update frontend tests for footer Terms link and checkout legal disclosure.
- [x] 3.2 Add a page-level test for Terms content/anchors, or otherwise cover the Terms page rendering with the available frontend test setup.
- [x] 3.3 Run OpenSpec validation and relevant frontend tests/build checks; fix issues found.
