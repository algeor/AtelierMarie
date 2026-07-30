# Manual smoke test — dynamic categories (managed taxonomy)

End-to-end verification that admin-managed taxonomy flows through the product
form, storefront filters, and product display. Corresponds to task 10.2 of the
`dynamic-categories` change.

## Preconditions
- Backend running (`make dev-backend`) and frontend running (`make dev-frontend`).
- Logged in as admin.

## Steps

1. **Create a product type "Boxes"**
   - Go to Admin → Taxonomy → Product types.
   - Add a term with English name "Boxes".
   - ✅ Expect: a row `boxes` appears, active, in-use count 0.

2. **Product type appears in the product form**
   - Go to Admin → Products → New (or edit an existing product).
   - Open the Product type dropdown.
   - ✅ Expect: "Boxes" is selectable (no code change/deploy needed).

3. **Assign a product to "Boxes"**
   - Create/edit a product, set Product type = Boxes, save.
   - ✅ Expect: save succeeds; product detail/admin shows product type Boxes.

4. **Product type appears in the storefront sidebar**
   - Go to the public `/products` page.
   - ✅ Expect: "Boxes" appears in the Product Type filter group; selecting it
     shows only Boxes products.

5. **Create a label "Winter"**
   - Admin → Taxonomy → Labels → add "Winter".
   - ✅ Expect: `winter` row appears, active.

6. **Assign "Winter" to a product**
   - Edit a product, tick the Winter label, save.
   - ✅ Expect: save succeeds; product detail shows a "Winter" tag.

7. **Filter by "Winter" on the storefront**
   - On `/products`, select the Winter label in the Labels filter group.
   - ✅ Expect: the grid narrows to products carrying the Winter label; a
     removable "Winter" chip shows above the grid.

8. **Deactivate "Winter"**
   - Admin → Taxonomy → Labels → Deactivate "Winter".
   - ✅ Expect: `winter` now shows as Retired.

9. **Deactivated label is hidden from filters but still displays on products**
   - Reload `/products`.
   - ✅ Expect: "Winter" no longer appears as a filter option in the Labels group.
   - Open the product that was tagged Winter.
   - ✅ Expect: the product detail STILL shows the "Winter" tag (retired terms
     remain visible on products that reference them).
   - In the admin product form for that product, the Winter label still shows
     (marked retired) and is preserved when saving unrelated edits.

## Notes
- Filtering is slug-based; localized display names (EN/BG) are shown in the UI
  but the filter matches the stable slug.
- A term that is still referenced by any product cannot be hard-deleted (the API
  returns 409 and the UI shows reassign/deactivate guidance); deactivate instead.
