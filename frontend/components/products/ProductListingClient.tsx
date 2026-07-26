"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import type { ProductResponse, TaxonomyResponse, TaxonomyTerm } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ProductGrid } from "./ProductGrid";
import { ProductCard } from "./ProductCard";

interface ProductListingClientProps {
  products: ProductResponse[];
  taxonomy: TaxonomyResponse;
}

/**
 * A single-select filter group (product type or category/tier). Declared at
 * module scope so its component identity is stable across renders — defining it
 * inside the parent would remount the whole group on every filter change.
 */
function SingleSelectGroup({
  title,
  terms,
  selected,
  onSelect,
}: {
  title: string;
  terms: TaxonomyTerm[];
  selected: string | null;
  onSelect: (slug: string | null) => void;
}) {
  if (terms.length === 0) return null;
  return (
    <div className="mb-6">
      <h3 className="mb-2 text-sm font-semibold text-charcoal">{title}</h3>
      <ul className="space-y-1">
        {terms.map((term) => {
          const active = selected === term.slug;
          return (
            <li key={term.slug}>
              <button
                type="button"
                aria-pressed={active}
                onClick={() => onSelect(active ? null : term.slug)}
                className={cn(
                  "w-full rounded-brand px-2 py-1.5 text-left text-sm transition-colors",
                  active
                    ? "bg-muted-gold text-charcoal"
                    : "text-soft-brown hover:bg-champagne-beige/50"
                )}
              >
                {term.name}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/**
 * Storefront product listing with faceted sidebar filters (product type,
 * category/tier, labels) plus an in-stock toggle. Filters are slug-based and
 * combine with AND semantics; the grid updates client-side without a reload.
 * Filter options come entirely from the public taxonomy endpoint — no hardcoded
 * taxonomy lists.
 */
export function ProductListingClient({ products, taxonomy }: ProductListingClientProps) {
  const t = useTranslations("products");
  const [productType, setProductType] = useState<string | null>(null);
  const [category, setCategory] = useState<string | null>(null);
  const [labels, setLabels] = useState<string[]>([]);
  const [inStockOnly, setInStockOnly] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  // Gate URL writes until after we've hydrated state from the URL, so the
  // initial write can't clobber incoming query params.
  const [hydrated, setHydrated] = useState(false);

  // Hydrate filter state from the URL once on mount (shareable/bookmarkable
  // filtered views). Done in an effect (not a useState initializer) to avoid a
  // server/client hydration mismatch.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const pt = params.get("type");
    const cat = params.get("category");
    const lbls = params.get("labels");
    if (pt) setProductType(pt);
    if (cat) setCategory(cat);
    if (lbls) setLabels(lbls.split(",").filter(Boolean));
    if (params.get("in_stock") === "1") setInStockOnly(true);
    setHydrated(true);
  }, []);

  // Reflect active filters back into the URL without triggering navigation.
  useEffect(() => {
    if (!hydrated) return;
    const params = new URLSearchParams();
    if (productType) params.set("type", productType);
    if (category) params.set("category", category);
    if (labels.length) params.set("labels", labels.join(","));
    if (inStockOnly) params.set("in_stock", "1");
    const qs = params.toString();
    window.history.replaceState(null, "", qs ? `?${qs}` : window.location.pathname);
  }, [hydrated, productType, category, labels, inStockOnly]);

  // Per-kind slug → localized name maps. Keyed by kind because a slug is only
  // unique within its kind (a category and a label could share one).
  const nameByKind = useMemo(
    () => ({
      type: new Map(taxonomy.product_types.map((term) => [term.slug, term.name])),
      category: new Map(taxonomy.categories.map((term) => [term.slug, term.name])),
      label: new Map(taxonomy.labels.map((term) => [term.slug, term.name])),
    }),
    [taxonomy]
  );

  const filtered = useMemo(
    () =>
      products.filter((p) => {
        if (productType && p.product_type !== productType) return false;
        if (category && p.category !== category) return false;
        if (labels.length && !labels.every((l) => p.labels.some((pl) => pl.slug === l))) {
          return false;
        }
        if (inStockOnly && p.stock <= 0) return false;
        return true;
      }),
    [products, productType, category, labels, inStockOnly]
  );

  function toggleLabel(slug: string) {
    setLabels((prev) => (prev.includes(slug) ? prev.filter((s) => s !== slug) : [...prev, slug]));
  }

  function clearAll() {
    setProductType(null);
    setCategory(null);
    setLabels([]);
    setInStockOnly(false);
  }

  const hasActiveFilters =
    productType !== null || category !== null || labels.length > 0 || inStockOnly;

  // Active filters as removable chips.
  const chips: { key: string; label: string; onRemove: () => void }[] = [];
  if (productType) {
    chips.push({
      key: `type:${productType}`,
      label: nameByKind.type.get(productType) ?? productType,
      onRemove: () => setProductType(null),
    });
  }
  if (category) {
    chips.push({
      key: `cat:${category}`,
      label: nameByKind.category.get(category) ?? category,
      onRemove: () => setCategory(null),
    });
  }
  for (const slug of labels) {
    chips.push({
      key: `label:${slug}`,
      label: nameByKind.label.get(slug) ?? slug,
      onRemove: () => toggleLabel(slug),
    });
  }

  const filterPanel = (
    <div>
      <SingleSelectGroup
        title={t("filterProductType")}
        terms={taxonomy.product_types}
        selected={productType}
        onSelect={setProductType}
      />
      <SingleSelectGroup
        title={t("filterCategory")}
        terms={taxonomy.categories}
        selected={category}
        onSelect={setCategory}
      />
      {taxonomy.labels.length > 0 && (
        <div className="mb-6">
          <h3 className="mb-2 text-sm font-semibold text-charcoal">{t("filterLabels")}</h3>
          <div className="flex flex-wrap gap-2">
            {taxonomy.labels.map((term) => {
              const active = labels.includes(term.slug);
              return (
                <button
                  key={term.slug}
                  type="button"
                  aria-pressed={active}
                  onClick={() => toggleLabel(term.slug)}
                  className={cn(
                    "rounded-pill px-3 py-1.5 text-sm transition-colors",
                    active
                      ? "bg-muted-gold text-charcoal"
                      : "bg-champagne-beige/50 text-soft-brown hover:bg-champagne-beige"
                  )}
                >
                  {term.name}
                </button>
              );
            })}
          </div>
        </div>
      )}
      <div className="mb-6">
        <label className="flex items-center gap-2 text-sm text-soft-brown">
          <input
            type="checkbox"
            checked={inStockOnly}
            onChange={(e) => setInStockOnly(e.target.checked)}
            className="h-4 w-4 rounded border-champagne-beige text-muted-gold focus:ring-muted-gold"
          />
          {t("inStockOnly")}
        </label>
      </div>
    </div>
  );

  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
      <h1 className="mb-8 font-heading text-3xl text-charcoal md:text-4xl">{t("title")}</h1>

      <div className="lg:grid lg:grid-cols-[220px_1fr] lg:gap-8">
        {/* Desktop sidebar */}
        <aside className="hidden lg:block">{filterPanel}</aside>

        <div>
          {/* Mobile filter toggle */}
          <div className="mb-4 lg:hidden">
            <button
              type="button"
              onClick={() => setMobileOpen((v) => !v)}
              aria-expanded={mobileOpen}
              className="rounded-brand border border-champagne-beige bg-cream px-4 py-2 text-sm font-medium text-soft-brown"
            >
              {t("filters")}
            </button>
            {mobileOpen && (
              <div className="mt-4 rounded-brand border border-champagne-beige bg-cream p-4">
                {filterPanel}
              </div>
            )}
          </div>

          {/* Active filter chips */}
          {chips.length > 0 && (
            <div className="mb-6 flex flex-wrap items-center gap-2">
              {chips.map((chip) => (
                <button
                  key={chip.key}
                  type="button"
                  onClick={chip.onRemove}
                  className="inline-flex items-center gap-1.5 rounded-pill bg-champagne-beige px-3 py-1 text-sm text-charcoal hover:bg-champagne-beige/70"
                >
                  {chip.label}
                  <span aria-hidden="true">×</span>
                </button>
              ))}
              {hasActiveFilters && (
                <button
                  type="button"
                  onClick={clearAll}
                  className="text-sm text-soft-brown underline hover:text-charcoal"
                >
                  {t("clearAll")}
                </button>
              )}
            </div>
          )}

          {/* Screen-reader result count */}
          <div aria-live="polite" role="status" className="sr-only">
            {t("resultsCount", { count: filtered.length })}
          </div>

          {filtered.length > 0 ? (
            <ProductGrid>
              {filtered.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </ProductGrid>
          ) : (
            <div className="py-16 text-center">
              <p className="text-lg text-soft-brown">
                {hasActiveFilters ? t("noMatch") : t("noProducts")}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
