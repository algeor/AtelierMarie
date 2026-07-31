"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import type { ProductResponse, TaxonomyResponse, TaxonomyTerm } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ProductGrid } from "./ProductGrid";
import { ProductCard } from "./ProductCard";

interface ProductListingClientProps {
  products: ProductResponse[];
  taxonomy: TaxonomyResponse;
}

interface ProductTypeSection {
  type: TaxonomyTerm;
  categories: TaxonomyTerm[];
  productCount: number;
}

/**
 * Storefront product listing with a drawer-based taxonomy menu. Product types
 * are top-level menu items; each expands to the categories used by that type.
 */
export function ProductListingClient({ products, taxonomy }: ProductListingClientProps) {
  const t = useTranslations("products");
  const [productType, setProductType] = useState<string | null>(null);
  const [category, setCategory] = useState<string | null>(null);
  const [labels, setLabels] = useState<string[]>([]);
  const [inStockOnly, setInStockOnly] = useState(false);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [expandedProductType, setExpandedProductType] = useState<string | null>(null);
  // Gate URL writes until after we've hydrated state from the URL, so the
  // initial write can't clobber incoming query params.
  const [hydrated, setHydrated] = useState(false);

  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLDivElement>(null);
  const returnFocusRef = useRef<Element | null>(null);

  // Hydrate filter state from the URL once on mount (shareable/bookmarkable
  // filtered views). Done in an effect (not a useState initializer) to avoid a
  // server/client hydration mismatch.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const pt = params.get("type");
    const cat = params.get("category");
    const lbls = params.get("labels");
    if (pt) {
      setProductType(pt);
      setExpandedProductType(pt);
    } else if (productTypeSections[0]) {
      // Expand the first section that actually has products, not the first raw
      // product type (which may have zero and would leave nothing expanded).
      setExpandedProductType(productTypeSections[0].type.slug);
    }
    if (cat) setCategory(cat);
    if (lbls) setLabels(lbls.split(",").filter(Boolean));
    if (params.get("in_stock") === "1") setInStockOnly(true);
    const q = params.get("q");
    const srt = params.get("sort");
    if (q) setSearch(q);
    if (srt) setSort(srt);
    setHydrated(true);
    // Mount-only: intentionally reads the initial-render section list once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Reflect active filters back into the URL without triggering navigation.
  useEffect(() => {
    if (!hydrated) return;
    const params = new URLSearchParams();
    if (productType) params.set("type", productType);
    if (category) params.set("category", category);
    if (labels.length) params.set("labels", labels.join(","));
    if (inStockOnly) params.set("in_stock", "1");
    if (search.trim()) params.set("q", search.trim());
    if (sort) params.set("sort", sort);
    const qs = params.toString();
    window.history.replaceState(null, "", qs ? `?${qs}` : window.location.pathname);
  }, [hydrated, productType, category, labels, inStockOnly, search, sort]);

  // Close on Escape, lock body scroll, and move focus into the drawer on open /
  // restore it to the trigger on close (modal-dialog behavior, mirroring CartDrawer).
  useEffect(() => {
    if (!menuOpen) return;

    returnFocusRef.current = document.activeElement;
    requestAnimationFrame(() => closeButtonRef.current?.focus());
    document.body.style.overflow = "hidden";

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);

    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
      if (returnFocusRef.current instanceof HTMLElement) {
        returnFocusRef.current.focus();
      }
      returnFocusRef.current = null;
    };
  }, [menuOpen]);

  // Focus trap: keep Tab / Shift+Tab cycling within the open drawer.
  const handleMenuKeyDown = useCallback((event: React.KeyboardEvent) => {
    if (event.key !== "Tab" || !drawerRef.current) return;
    const focusable = drawerRef.current.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'
    );
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (!first || !last) return;
    if (event.shiftKey) {
      if (document.activeElement === first) {
        event.preventDefault();
        last.focus();
      }
    } else if (document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }, []);

  // Per-kind slug -> localized name maps. Keyed by kind because a slug is only
  // unique within its kind (a category and a label could share one).
  const nameByKind = useMemo(
    () => ({
      type: new Map(taxonomy.product_types.map((term) => [term.slug, term.name])),
      category: new Map(taxonomy.categories.map((term) => [term.slug, term.name])),
      label: new Map(taxonomy.labels.map((term) => [term.slug, term.name])),
    }),
    [taxonomy]
  );

  const productTypeSections = useMemo<ProductTypeSection[]>(() => {
    return taxonomy.product_types
      .map((type) => {
        const typeProducts = products.filter((product) => product.product_type === type.slug);
        const usedCategorySlugs = new Set(
          typeProducts
            .filter((product) => product.category !== null)
            .map((product) => product.category as string)
        );

        return {
          type,
          categories: taxonomy.categories.filter((term) => usedCategorySlugs.has(term.slug)),
          productCount: typeProducts.length,
        };
      })
      .filter((section) => section.productCount > 0);
  }, [products, taxonomy]);

  const visibleLabels = useMemo(() => {
    const usedLabelSlugs = new Set(
      products.flatMap((product) => product.labels.map((label) => label.slug))
    );
    return taxonomy.labels.filter((term) => usedLabelSlugs.has(term.slug));
  }, [products, taxonomy.labels]);

  useEffect(() => {
    if (!hydrated) return;

    const validProductTypes = new Set(productTypeSections.map((section) => section.type.slug));
    const validLabels = new Set(visibleLabels.map((term) => term.slug));
    const scopedProducts = productType
      ? products.filter((product) => product.product_type === productType)
      : products;
    const validCategories = new Set(
      scopedProducts
        .filter((product) => product.category !== null)
        .map((product) => product.category as string)
    );

    if (productType && !validProductTypes.has(productType)) {
      setProductType(null);
      setCategory(null);
    } else if (category && !validCategories.has(category)) {
      setCategory(null);
    }

    const nextLabels = labels.filter((label) => validLabels.has(label));
    if (nextLabels.length !== labels.length) {
      setLabels(nextLabels);
    }
  }, [category, hydrated, labels, productType, productTypeSections, products, visibleLabels]);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    const matched = products.filter((p) => {
      if (productType && p.product_type !== productType) return false;
      if (category && p.category !== category) return false;
      if (labels.length && !labels.every((l) => p.labels.some((pl) => pl.slug === l))) {
        return false;
      }
      if (inStockOnly && p.stock <= 0) return false;
      if (query && !`${p.name} ${p.description ?? ""}`.toLowerCase().includes(query)) {
        return false;
      }
      return true;
    });

    const sorted = [...matched];
    switch (sort) {
      case "price_asc":
        sorted.sort((a, b) => a.effective_price_cents - b.effective_price_cents);
        break;
      case "price_desc":
        sorted.sort((a, b) => b.effective_price_cents - a.effective_price_cents);
        break;
      case "name":
        sorted.sort((a, b) => a.name.localeCompare(b.name));
        break;
      case "newest":
        sorted.sort((a, b) => b.created_at.localeCompare(a.created_at));
        break;
      default:
        break;
    }
    return sorted;
  }, [products, productType, category, labels, inStockOnly, search, sort]);

  const sortOptions = [
    { value: "", labelKey: "sortRelevance" },
    { value: "newest", labelKey: "sortNewest" },
    { value: "price_asc", labelKey: "sortPriceAsc" },
    { value: "price_desc", labelKey: "sortPriceDesc" },
    { value: "name", labelKey: "sortName" },
  ] as const;

  function toggleLabel(slug: string) {
    setLabels((prev) => (prev.includes(slug) ? prev.filter((s) => s !== slug) : [...prev, slug]));
  }

  function selectProductType(slug: string) {
    setProductType((current) => (current === slug && category === null ? null : slug));
    setCategory(null);
    setExpandedProductType(slug);
  }

  function selectProductTypeCategory(typeSlug: string, categorySlug: string | null) {
    setProductType(typeSlug);
    setCategory(categorySlug);
    setExpandedProductType(typeSlug);
    setMenuOpen(false);
  }

  function clearAll() {
    setProductType(null);
    setCategory(null);
    setLabels([]);
    setInStockOnly(false);
    setSearch("");
  }

  const hasActiveFilters =
    productType !== null ||
    category !== null ||
    labels.length > 0 ||
    inStockOnly ||
    search.trim() !== "";
  const activeFilterCount =
    (productType ? 1 : 0) +
    (category ? 1 : 0) +
    labels.length +
    (inStockOnly ? 1 : 0) +
    (search.trim() ? 1 : 0);

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
  if (search.trim()) {
    chips.push({
      key: "q",
      label: `“${search.trim()}”`,
      onRemove: () => setSearch(""),
    });
  }

  const menuPanel = (
    <>
      <div className="border-b border-champagne-beige px-5 py-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-heading text-xl text-charcoal">{t("productMenu")}</h2>
          <button
            ref={closeButtonRef}
            type="button"
            onClick={() => setMenuOpen(false)}
            aria-label={t("closeProductMenu")}
            className="inline-flex h-10 w-10 items-center justify-center rounded-brand text-soft-brown hover:bg-champagne-beige/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-cream"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="h-5 w-5"
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-5">
        <div className="mb-4 space-y-3">
          <div>
            <label htmlFor="product-search" className="sr-only">
              {t("searchLabel")}
            </label>
            <input
              id="product-search"
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t("searchPlaceholder")}
              className="w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm text-charcoal placeholder:text-soft-brown/60 focus:border-muted-gold focus:outline-none focus:ring-1 focus:ring-muted-gold"
            />
          </div>
          <div>
            <label htmlFor="product-sort" className="sr-only">
              {t("sortLabel")}
            </label>
            <select
              id="product-sort"
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              className="w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm text-charcoal focus:border-muted-gold focus:outline-none focus:ring-1 focus:ring-muted-gold"
            >
              {sortOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {t(opt.labelKey)}
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          type="button"
          onClick={() => {
            clearAll();
            setMenuOpen(false);
          }}
          className={cn(
            "mb-4 flex w-full items-center justify-between rounded-brand px-3 py-2.5 text-left text-sm font-medium transition-colors",
            hasActiveFilters
              ? "text-soft-brown hover:bg-champagne-beige/50 hover:text-charcoal"
              : "bg-muted-gold/15 text-charcoal"
          )}
        >
          <span>{t("allProducts")}</span>
          <span className="text-xs text-soft-brown">{products.length}</span>
        </button>

        <div className="space-y-2" aria-label={t("filterProductType")}>
          {productTypeSections.map(({ type, categories, productCount }) => {
            const expanded = expandedProductType === type.slug;
            const activeType = productType === type.slug;
            const panelId = `product-menu-${type.slug}`;
            return (
              <div key={type.slug} className="rounded-brand border border-champagne-beige bg-warm-ivory">
                <button
                  type="button"
                  aria-expanded={expanded}
                  aria-controls={panelId}
                  aria-pressed={activeType && category === null}
                  onClick={() => selectProductType(type.slug)}
                  className={cn(
                    "flex w-full items-center justify-between gap-3 rounded-brand px-3 py-3 text-left text-sm font-semibold transition-colors",
                    activeType
                      ? "bg-muted-gold/15 text-charcoal"
                      : "text-soft-brown hover:bg-champagne-beige/50 hover:text-charcoal"
                  )}
                >
                  <span>{type.name}</span>
                  <span className="inline-flex items-center gap-2 text-xs font-normal text-soft-brown">
                    {productCount}
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                      className={cn("h-4 w-4 transition-transform", expanded && "rotate-180")}
                      aria-hidden="true"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                    </svg>
                  </span>
                </button>

                {expanded && (
                  <div id={panelId} className="border-t border-champagne-beige px-3 py-3">
                    <button
                      type="button"
                      onClick={() => selectProductTypeCategory(type.slug, null)}
                      aria-pressed={activeType && category === null}
                      className={cn(
                        "mb-1 w-full rounded-brand px-3 py-2 text-left text-sm transition-colors",
                        activeType && category === null
                          ? "bg-muted-gold text-charcoal"
                          : "text-soft-brown hover:bg-champagne-beige/60 hover:text-charcoal"
                      )}
                    >
                      {t("allCategories")}
                    </button>
                    <div className="space-y-1">
                      {categories.map((term) => {
                        const activeCategory = activeType && category === term.slug;
                        return (
                          <button
                            key={`${type.slug}:${term.slug}`}
                            type="button"
                            onClick={() => selectProductTypeCategory(type.slug, term.slug)}
                            aria-pressed={activeCategory}
                            className={cn(
                              "w-full rounded-brand px-3 py-2 text-left text-sm transition-colors",
                              activeCategory
                                ? "bg-muted-gold text-charcoal"
                                : "text-soft-brown hover:bg-champagne-beige/60 hover:text-charcoal"
                            )}
                          >
                            {term.name}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {visibleLabels.length > 0 && (
          <div className="mt-6 border-t border-champagne-beige pt-5">
            <h3 className="mb-2 text-sm font-semibold text-charcoal">{t("filterLabels")}</h3>
            <div className="flex flex-wrap gap-2">
              {visibleLabels.map((term) => {
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

        <div className="mt-6">
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
    </>
  );

  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
      <div className="mb-8 flex items-center justify-between gap-4">
        <h1 className="min-w-0 font-heading text-3xl text-charcoal md:text-4xl">{t("title")}</h1>
        <button
          type="button"
          onClick={() => setMenuOpen(true)}
          aria-expanded={menuOpen}
          aria-controls="product-taxonomy-menu"
          aria-label={t("openProductMenu")}
          className="group inline-flex min-h-[52px] shrink-0 items-center gap-3 rounded-pill pl-2 text-right transition-transform motion-safe:duration-200 motion-safe:ease-brand hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
        >
          <span className="hidden flex-col items-end sm:flex">
            <span className="text-sm font-semibold text-charcoal">{t("shopByType")}</span>
            <span className="text-xs text-soft-brown">{t("productMenu")}</span>
          </span>
          <span className="relative inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-charcoal text-cream shadow-lg shadow-charcoal/15 transition-colors group-hover:bg-soft-brown">
            <span className="flex h-4 w-5 flex-col justify-between" aria-hidden="true">
              <span className="h-[2px] w-5 rounded-full bg-current transition-transform group-hover:translate-x-0.5" />
              <span className="h-[2px] w-3.5 self-end rounded-full bg-current transition-all group-hover:w-5" />
              <span className="h-[2px] w-5 rounded-full bg-current transition-transform group-hover:-translate-x-0.5" />
            </span>
            {hasActiveFilters && (
              <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-muted-gold px-1 text-[10px] font-semibold leading-none text-charcoal ring-2 ring-warm-ivory">
                {activeFilterCount}
              </span>
            )}
          </span>
        </button>
      </div>

      {menuOpen && (
        <div
          className="product-menu-backdrop fixed inset-0 z-40 bg-charcoal/35 backdrop-blur-[2px]"
          onClick={() => setMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      {menuOpen && (
        <aside
          ref={drawerRef}
          id="product-taxonomy-menu"
          role="dialog"
          aria-modal="true"
          onKeyDown={handleMenuKeyDown}
          className="product-menu-drawer fixed inset-y-0 left-0 z-50 flex w-[min(22rem,calc(100vw-2rem))] flex-col border-r border-champagne-beige bg-cream shadow-2xl shadow-charcoal/20"
          aria-label={t("productMenu")}
        >
          {menuPanel}
        </aside>
      )}

      <div>
        {/* Active filter chips */}
        {chips.length > 0 && (
          <div className="mb-6 flex flex-wrap items-center gap-2">
            {chips.map((chip) => (
              <button
                key={chip.key}
                type="button"
                onClick={chip.onRemove}
                aria-label={t("removeFilter", { name: chip.label })}
                className="inline-flex items-center gap-1.5 rounded-pill bg-champagne-beige px-3 py-1 text-sm text-charcoal hover:bg-champagne-beige/70"
              >
                {chip.label}
                <span aria-hidden="true">x</span>
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
  );
}
