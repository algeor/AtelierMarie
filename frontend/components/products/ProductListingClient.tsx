"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useTransition,
} from "react";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import type {
  ProductListQuery,
  ProductListSort,
  ProductResponse,
  TaxonomyResponse,
  TaxonomyTerm,
} from "@/lib/types";
import { cn } from "@/lib/utils";
import { trackAnalytics } from "@/lib/analytics";
import { ProductGrid } from "./ProductGrid";
import { ProductCard } from "./ProductCard";

interface ProductListingClientProps {
  products: ProductResponse[];
  taxonomy: TaxonomyResponse;
  total: number;
  page: number;
  limit: number;
  filters: ProductListQuery;
}

interface ProductTypeSection {
  type: TaxonomyTerm;
  categories: TaxonomyTerm[];
}

interface ListingState {
  productType: string | null;
  category: string | null;
  labels: string[];
  inStockOnly: boolean;
  search: string;
  sort: ProductListSort | "";
}

const DEFAULT_PRODUCT_LIMIT = 24;

/**
 * Storefront product listing with a drawer-based taxonomy menu. The route owns
 * result filtering; this client only updates query params and renders the
 * server-returned product page.
 */
export function ProductListingClient({
  products,
  taxonomy,
  total,
  page,
  limit,
  filters,
}: ProductListingClientProps) {
  const t = useTranslations("products");
  const tCommon = useTranslations("common");
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();
  const [productType, setProductType] = useState<string | null>(
    filters.product_type ?? null,
  );
  const [category, setCategory] = useState<string | null>(
    filters.category ?? null,
  );
  const [labels, setLabels] = useState<string[]>(filters.labels ?? []);
  const [inStockOnly, setInStockOnly] = useState(filters.in_stock ?? false);
  const [search, setSearch] = useState(filters.q ?? "");
  const [sort, setSort] = useState<ProductListSort | "">(filters.sort ?? "");
  const [menuOpen, setMenuOpen] = useState(false);
  const [expandedProductType, setExpandedProductType] = useState<string | null>(
    filters.product_type ?? taxonomy.product_types[0]?.slug ?? null,
  );

  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLDivElement>(null);
  const returnFocusRef = useRef<Element | null>(null);
  const lastFilterSignatureRef = useRef("");

  const currentListingState = useMemo<ListingState>(
    () => ({ productType, category, labels, inStockOnly, search, sort }),
    [category, inStockOnly, labels, productType, search, sort],
  );

  const committedDiscoveryFilters = useMemo(() => {
    const parts = [
      filters.product_type ? `type:${filters.product_type}` : null,
      filters.category ? `category:${filters.category}` : null,
      ...(filters.labels ?? []).map((label) => `label:${label}`),
      filters.in_stock ? "availability:in_stock" : null,
    ].filter(Boolean);
    return parts.length > 0 ? parts.join("|") : undefined;
  }, [filters.category, filters.in_stock, filters.labels, filters.product_type]);

  useEffect(() => {
    const nextProductType = filters.product_type ?? null;
    setProductType(nextProductType);
    setCategory(filters.category ?? null);
    setLabels(filters.labels ?? []);
    setInStockOnly(filters.in_stock ?? false);
    setSearch(filters.q ?? "");
    setSort(filters.sort ?? "");
    setExpandedProductType(
      nextProductType ?? taxonomy.product_types[0]?.slug ?? null,
    );
  }, [
    filters.category,
    filters.in_stock,
    filters.labels,
    filters.product_type,
    filters.q,
    filters.sort,
    taxonomy.product_types,
  ]);

  const navigateToListing = useCallback(
    (next: ListingState, nextPage = 1) => {
      const params = new URLSearchParams();
      if (next.productType) params.set("type", next.productType);
      if (next.category) params.set("category", next.category);
      if (next.labels.length) params.set("labels", next.labels.join(","));
      if (next.inStockOnly) params.set("in_stock", "1");
      if (next.search.trim()) params.set("q", next.search.trim());
      if (next.sort) params.set("sort", next.sort);
      if (nextPage > 1) params.set("page", String(nextPage));
      if (limit !== DEFAULT_PRODUCT_LIMIT) params.set("limit", String(limit));

      const qs = params.toString();
      const href = `${pathname}${qs ? `?${qs}` : ""}`;
      startTransition(() => {
        router.replace(href, { scroll: false });
      });
    },
    [limit, pathname, router],
  );

  const commitListingState = useCallback(
    (next: ListingState, nextPage = 1) => {
      setProductType(next.productType);
      setCategory(next.category);
      setLabels(next.labels);
      setInStockOnly(next.inStockOnly);
      setSearch(next.search);
      setSort(next.sort);
      navigateToListing(next, nextPage);
    },
    [navigateToListing],
  );

  const commitPatch = useCallback(
    (patch: Partial<ListingState>, nextPage = 1) => {
      commitListingState({ ...currentListingState, ...patch }, nextPage);
    },
    [commitListingState, currentListingState],
  );

  useEffect(() => {
    if (search.trim() === (filters.q ?? "")) return;
    const handle = window.setTimeout(() => {
      commitListingState(currentListingState, 1);
    }, 350);
    return () => window.clearTimeout(handle);
  }, [commitListingState, currentListingState, filters.q, search]);

  useEffect(() => {
    const analyticsProductType = filters.product_type ?? null;
    const analyticsCategory = filters.category ?? null;
    const analyticsLabels = filters.labels ?? [];
    const analyticsInStockOnly = filters.in_stock ?? false;
    const analyticsSort = filters.sort ?? "";
    const signature = JSON.stringify({
      productType: analyticsProductType,
      category: analyticsCategory,
      labels: analyticsLabels,
      inStockOnly: analyticsInStockOnly,
      sort: analyticsSort,
      shown: products.length,
      total,
    });
    if (signature === lastFilterSignatureRef.current) return;
    lastFilterSignatureRef.current = signature;

    const commonProperties = {
      listing_context: "products",
      active_filters: committedDiscoveryFilters,
      sort: analyticsSort || undefined,
      result_count: products.length,
      total_count: total,
    };

    if (analyticsProductType) {
      trackAnalytics("listing_filter", {
        ...commonProperties,
        filter_name: "product_type",
        filter_value: analyticsProductType,
      });
    }
    if (analyticsCategory) {
      trackAnalytics("listing_filter", {
        ...commonProperties,
        filter_name: "category",
        filter_value: analyticsCategory,
      });
    }
    for (const label of analyticsLabels) {
      trackAnalytics("listing_filter", {
        ...commonProperties,
        filter_name: "label",
        filter_value: label,
      });
    }
    if (analyticsInStockOnly) {
      trackAnalytics("listing_filter", {
        ...commonProperties,
        filter_name: "availability",
        filter_value: "in_stock",
      });
    }
    if (analyticsSort) {
      trackAnalytics("listing_filter", {
        ...commonProperties,
        filter_name: "sort",
        filter_value: analyticsSort,
      });
    }
  }, [
    committedDiscoveryFilters,
    filters.category,
    filters.in_stock,
    filters.labels,
    filters.product_type,
    filters.sort,
    products.length,
    total,
  ]);

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
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])',
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
      type: new Map(
        taxonomy.product_types.map((term) => [term.slug, term.name]),
      ),
      category: new Map(
        taxonomy.categories.map((term) => [term.slug, term.name]),
      ),
      label: new Map(taxonomy.labels.map((term) => [term.slug, term.name])),
    }),
    [taxonomy],
  );

  const productTypeSections = useMemo<ProductTypeSection[]>(() => {
    return taxonomy.product_types.map((type) => ({
      type,
      categories: taxonomy.categories,
    }));
  }, [taxonomy.categories, taxonomy.product_types]);

  const visibleLabels = taxonomy.labels;

  const sortOptions = [
    { value: "", labelKey: "sortRelevance" },
    { value: "newest", labelKey: "sortNewest" },
    { value: "price_asc", labelKey: "sortPriceAsc" },
    { value: "price_desc", labelKey: "sortPriceDesc" },
    { value: "name", labelKey: "sortName" },
  ] as const;

  function toggleLabel(slug: string) {
    const nextLabels = labels.includes(slug)
      ? labels.filter((s) => s !== slug)
      : [...labels, slug];
    commitPatch({ labels: nextLabels });
  }

  function selectProductType(slug: string) {
    const nextProductType = productType === slug && category === null ? null : slug;
    commitPatch({ productType: nextProductType, category: null });
    setExpandedProductType(slug);
  }

  function selectProductTypeCategory(
    typeSlug: string,
    categorySlug: string | null,
  ) {
    commitPatch({ productType: typeSlug, category: categorySlug });
    setExpandedProductType(typeSlug);
    setMenuOpen(false);
  }

  function clearAll() {
    commitListingState(
      {
        ...currentListingState,
        productType: null,
        category: null,
        labels: [],
        inStockOnly: false,
        search: "",
      },
      1,
    );
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
      onRemove: () => commitPatch({ productType: null, category: null }),
    });
  }
  if (category) {
    chips.push({
      key: `cat:${category}`,
      label: nameByKind.category.get(category) ?? category,
      onRemove: () => commitPatch({ category: null }),
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
      onRemove: () => commitPatch({ search: "" }),
    });
  }

  const pageCount = Math.max(1, Math.ceil(total / limit));
  const canGoPrevious = page > 1;
  const canGoNext = page < pageCount;

  function goToPage(nextPage: number) {
    commitListingState(
      currentListingState,
      Math.min(Math.max(nextPage, 1), pageCount),
    );
  }

  const menuPanel = (
    <>
      <div className="border-b editorial-divider px-5 py-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-heading text-xl text-text">{t("productMenu")}</h2>
          <button
            ref={closeButtonRef}
            type="button"
            onClick={() => setMenuOpen(false)}
            aria-label={t("closeProductMenu")}
            className="inline-flex h-10 w-10 items-center justify-center rounded-brand text-muted hover:bg-surface/55 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
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
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
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
              className="w-full rounded-brand border border-border/35 bg-page/70 px-3 py-2 text-sm text-text placeholder:text-muted/60 focus:border-focus focus:outline-none focus:ring-1 focus:ring-focus"
            />
          </div>
          <div>
            <label htmlFor="product-sort" className="sr-only">
              {t("sortLabel")}
            </label>
            <select
              id="product-sort"
              value={sort}
              onChange={(e) =>
                commitPatch({ sort: e.target.value as ProductListSort | "" })
              }
              className="w-full rounded-brand border border-border/35 bg-page/70 px-3 py-2 text-sm text-text focus:border-focus focus:outline-none focus:ring-1 focus:ring-focus"
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
              ? "text-muted hover:bg-surface/55 hover:text-text"
              : "bg-accent-soft/35 text-text",
          )}
        >
          <span>{t("allProducts")}</span>
        </button>

        <div className="space-y-2" aria-label={t("filterProductType")}>
          {productTypeSections.map(({ type, categories }) => {
            const expanded = expandedProductType === type.slug;
            const activeType = productType === type.slug;
            const panelId = `product-menu-${type.slug}`;
            return (
              <div
                key={type.slug}
                className="editorial-paper-panel rounded-brand"
              >
                <button
                  type="button"
                  aria-expanded={expanded}
                  aria-controls={panelId}
                  aria-pressed={activeType && category === null}
                  onClick={() => selectProductType(type.slug)}
                  className={cn(
                    "flex w-full items-center justify-between gap-3 rounded-brand px-3 py-3 text-left text-sm font-semibold transition-colors",
                    activeType
                      ? "bg-accent-soft/35 text-text"
                      : "text-muted hover:bg-surface/55 hover:text-text",
                  )}
                >
                  <span>{type.name}</span>
                  <span className="inline-flex items-center gap-2 text-xs font-normal text-muted">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                      className={cn(
                        "h-4 w-4 transition-transform",
                        expanded && "rotate-180",
                      )}
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M19.5 8.25l-7.5 7.5-7.5-7.5"
                      />
                    </svg>
                  </span>
                </button>

                {expanded && (
                  <div
                    id={panelId}
                    className="border-t editorial-divider px-3 py-3"
                  >
                    <button
                      type="button"
                      onClick={() => selectProductTypeCategory(type.slug, null)}
                      aria-pressed={activeType && category === null}
                      className={cn(
                        "mb-1 w-full rounded-brand px-3 py-2 text-left text-sm transition-colors",
                        activeType && category === null
                          ? "bg-primary/75 text-primary-foreground"
                          : "text-muted hover:bg-surface/60 hover:text-text",
                      )}
                    >
                      {t("allCategories")}
                    </button>
                    <div className="space-y-1">
                      {categories.map((term) => {
                        const activeCategory =
                          activeType && category === term.slug;
                        return (
                          <button
                            key={`${type.slug}:${term.slug}`}
                            type="button"
                            onClick={() =>
                              selectProductTypeCategory(type.slug, term.slug)
                            }
                            aria-pressed={activeCategory}
                            className={cn(
                              "w-full rounded-brand px-3 py-2 text-left text-sm transition-colors",
                              activeCategory
                                ? "bg-primary/75 text-primary-foreground"
                                : "text-muted hover:bg-surface/60 hover:text-text",
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
          <div className="mt-6 border-t editorial-divider pt-5">
            <h3 className="mb-2 text-sm font-semibold text-text">
              {t("filterLabels")}
            </h3>
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
                        ? "bg-primary/75 text-primary-foreground"
                        : "bg-surface/60 text-muted hover:bg-surface hover:text-text",
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
          <label className="flex items-center gap-2 text-sm text-muted">
            <input
              type="checkbox"
              checked={inStockOnly}
              onChange={(e) => commitPatch({ inStockOnly: e.target.checked })}
              className="h-4 w-4 rounded border-border/50 text-primary focus:ring-focus"
            />
            {t("inStockOnly")}
          </label>
        </div>
      </div>
    </>
  );

  return (
    <section className="editorial-band px-4 py-12 text-text sm:px-6 lg:px-8 lg:py-16">
      <div className="mx-auto max-w-7xl">
        <div className="mb-10 flex items-center justify-between gap-4 border-b editorial-divider pb-8">
          <h1 className="min-w-0 font-heading text-3xl text-text md:text-4xl">
            {t("title")}
          </h1>
          <button
            type="button"
            onClick={() => setMenuOpen(true)}
            aria-expanded={menuOpen}
            aria-controls="product-taxonomy-menu"
            aria-label={t("openProductMenu")}
            className="group inline-flex min-h-[52px] shrink-0 items-center gap-3 rounded-pill pl-2 text-right transition-transform motion-safe:duration-200 motion-safe:ease-brand hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
          >
            <span className="hidden flex-col items-end sm:flex">
              <span className="text-sm font-semibold text-text">
                {t("shopByType")}
              </span>
              <span className="text-xs text-muted">{t("productMenu")}</span>
            </span>
            <span className="relative inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-text text-page shadow-lg shadow-text/15 transition-colors group-hover:bg-muted">
              <span
                className="flex h-4 w-5 flex-col justify-between"
                aria-hidden="true"
              >
                <span className="h-[2px] w-5 rounded-full bg-current transition-transform group-hover:translate-x-0.5" />
                <span className="h-[2px] w-3.5 self-end rounded-full bg-current transition-all group-hover:w-5" />
                <span className="h-[2px] w-5 rounded-full bg-current transition-transform group-hover:-translate-x-0.5" />
              </span>
              {hasActiveFilters && (
                <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-semibold leading-none text-primary-foreground ring-2 ring-page">
                  {activeFilterCount}
                </span>
              )}
            </span>
          </button>
        </div>

        {menuOpen && (
          <div
            className="product-menu-backdrop fixed inset-0 z-40 bg-text/35 backdrop-blur-[2px]"
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
            className="product-menu-drawer fixed inset-y-0 left-0 z-50 flex w-[min(22rem,calc(100vw-2rem))] flex-col border-r border-border/30 bg-page/95 shadow-2xl shadow-text/16 backdrop-blur-xl"
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
                  className="inline-flex items-center gap-1.5 rounded-pill bg-surface/70 px-3 py-1 text-sm text-text hover:bg-surface"
                >
                  {chip.label}
                  <span aria-hidden="true">x</span>
                </button>
              ))}
              {hasActiveFilters && (
                <button
                  type="button"
                  onClick={clearAll}
                  className="text-sm text-muted underline hover:text-text"
                >
                  {t("clearAll")}
                </button>
              )}
            </div>
          )}

          <div
            aria-live="polite"
            aria-busy={isPending}
            role="status"
            className="mb-6 text-sm text-muted"
          >
            {t("resultsSummary", { shown: products.length, total })}
          </div>

          {products.length > 0 ? (
            <ProductGrid>
              {products.map((product, index) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  index={(page - 1) * limit + index}
                  listingContext="products"
                  activeFilters={committedDiscoveryFilters}
                  sort={filters.sort}
                  resultCount={products.length}
                  totalCount={total}
                />
              ))}
            </ProductGrid>
          ) : (
            <div className="py-16 text-center">
              <p className="text-lg text-muted">
                {hasActiveFilters ? t("noMatch") : t("noProducts")}
              </p>
            </div>
          )}

          {pageCount > 1 && (
            <nav
              aria-label={t("paginationLabel")}
              className="mt-10 flex items-center justify-center gap-4"
            >
              <button
                type="button"
                disabled={!canGoPrevious || isPending}
                onClick={() => goToPage(page - 1)}
                className="rounded-brand border border-border/35 px-4 py-2 text-sm font-medium text-text disabled:cursor-not-allowed disabled:opacity-45 enabled:hover:bg-surface/60"
              >
                {tCommon("previous")}
              </button>
              <span className="text-sm text-muted">
                {tCommon("page", { current: page, total: pageCount })}
              </span>
              <button
                type="button"
                disabled={!canGoNext || isPending}
                onClick={() => goToPage(page + 1)}
                className="rounded-brand border border-border/35 px-4 py-2 text-sm font-medium text-text disabled:cursor-not-allowed disabled:opacity-45 enabled:hover:bg-surface/60"
              >
                {tCommon("next")}
              </button>
            </nav>
          )}
        </div>
      </div>
    </section>
  );
}
