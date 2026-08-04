"use client";

import { useCallback, useEffect, useMemo, useState, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { deleteProduct, getAdminProducts, getAdminTaxonomy, updateProduct } from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { useLocalizedError } from "@/lib/useLocalizedError";
import { formatPrice } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { DeleteIconButton } from "@/components/ui/DeleteIconButton";
import { Skeleton } from "@/components/ui/Skeleton";
import { SaveConfirmation } from "@/components/admin/SaveConfirmation";
import { ProductBulkDiscountBar } from "@/components/admin/promotions/ProductBulkDiscountBar";
import type {
  AdminProductDiscountFilter,
  AdminProductFilters,
  AdminProductInventoryModeFilter,
  AdminProductMediaFilter,
  AdminProductRecipeStatusFilter,
  AdminProductResponse,
  AdminProductSort,
  AdminProductStatusFilter,
  AdminProductStockFilter,
  AdminTaxonomyTerm,
} from "@/lib/types";

const DEFAULT_FILTERS: Required<Pick<AdminProductFilters, "status" | "media" | "stock" | "discount" | "sort">> &
  Omit<AdminProductFilters, "status" | "media" | "stock" | "discount" | "sort"> = {
  q: "",
  status: "all",
  media: "any",
  stock: "any",
  product_type: "",
  category: "",
  label: [],
  featured: null,
  discount: "any",
  inventory_mode: "",
  recipe_status: "",
  has_inventory_exceptions: null,
  low_stock_threshold: 5,
  sort: "created_desc",
};

function booleanParam(value: string | null): boolean | null {
  if (value === "true") return true;
  if (value === "false") return false;
  return null;
}

function filtersFromParams(params: URLSearchParams): AdminProductFilters {
  return {
    ...DEFAULT_FILTERS,
    q: params.get("q") ?? "",
    status: (params.get("status") as AdminProductStatusFilter | null) ?? "all",
    media: (params.get("media") as AdminProductMediaFilter | null) ?? "any",
    stock: (params.get("stock") as AdminProductStockFilter | null) ?? "any",
    product_type: params.get("product_type") ?? "",
    category: params.get("category") ?? "",
    label: params.getAll("label"),
    featured: booleanParam(params.get("featured")),
    discount: (params.get("discount") as AdminProductDiscountFilter | null) ?? "any",
    inventory_mode: (params.get("inventory_mode") as AdminProductInventoryModeFilter | null) ?? "",
    recipe_status: (params.get("recipe_status") as AdminProductRecipeStatusFilter | null) ?? "",
    has_inventory_exceptions: booleanParam(params.get("has_inventory_exceptions")),
    low_stock_threshold: Number(params.get("low_stock_threshold") ?? 5),
    sort: (params.get("sort") as AdminProductSort | null) ?? "created_desc",
  };
}

function filtersToParams(filters: AdminProductFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.q?.trim()) params.set("q", filters.q.trim());
  if (filters.status && filters.status !== "all") params.set("status", filters.status);
  if (filters.media && filters.media !== "any") params.set("media", filters.media);
  if (filters.stock && filters.stock !== "any") params.set("stock", filters.stock);
  if (filters.product_type) params.set("product_type", filters.product_type);
  if (filters.category) params.set("category", filters.category);
  for (const label of filters.label ?? []) params.append("label", label);
  if (filters.featured !== null && filters.featured !== undefined) params.set("featured", String(filters.featured));
  if (filters.discount && filters.discount !== "any") params.set("discount", filters.discount);
  if (filters.inventory_mode) params.set("inventory_mode", filters.inventory_mode);
  if (filters.recipe_status) params.set("recipe_status", filters.recipe_status);
  if (filters.has_inventory_exceptions !== null && filters.has_inventory_exceptions !== undefined) {
    params.set("has_inventory_exceptions", String(filters.has_inventory_exceptions));
  }
  if (filters.stock === "low" && filters.low_stock_threshold !== 5) {
    params.set("low_stock_threshold", String(filters.low_stock_threshold));
  }
  if (filters.sort && filters.sort !== "created_desc") params.set("sort", filters.sort);
  return params;
}

export default function AdminProductsPage() {
  const t = useTranslations("admin");
  const tCommon = useTranslations("common");
  const getLocalizedError = useLocalizedError();
  const searchParams = useSearchParams();
  const [products, setProducts] = useState<AdminProductResponse[]>([]);
  const [totalProducts, setTotalProducts] = useState(0);
  const [filters, setFilters] = useState<AdminProductFilters>(() =>
    filtersFromParams(new URLSearchParams(searchParams.toString()))
  );
  const [productTypes, setProductTypes] = useState<AdminTaxonomyTerm[]>([]);
  const [categories, setCategories] = useState<AdminTaxonomyTerm[]>([]);
  const [labels, setLabels] = useState<AdminTaxonomyTerm[]>([]);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [successNoticeId, setSuccessNoticeId] = useState(0);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const selectAllRef = useRef<HTMLInputElement>(null);
  const successTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Show success banner from query param
  useEffect(() => {
    const success = searchParams.get("success");
    const messages: Record<string, string> = {
      created: t("productCreated"),
      updated: t("productUpdated"),
    };
    if (success && messages[success]) {
      showSuccess(messages[success]);
      // Strip param from URL to prevent re-flash on refresh
      const params = new URLSearchParams(window.location.search);
      params.delete("success");
      const query = params.toString();
      window.history.replaceState(
        {},
        "",
        `${window.location.pathname}${query ? `?${query}` : ""}`
      );
    }
    return () => {
      if (successTimerRef.current) clearTimeout(successTimerRef.current);
    };
  }, [searchParams, t]);

  const loadProducts = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await getAdminProducts(1, 100, filters);
      setProducts(data.products);
      setTotalProducts(data.total);
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("errors.loadProducts"));
    } finally {
      setIsLoading(false);
    }
  }, [filters, getLocalizedError, t]);

  useEffect(() => {
    loadProducts();
  }, [loadProducts]);

  useEffect(() => {
    let cancelled = false;
    async function loadTaxonomy() {
      try {
        const [typeTerms, categoryTerms, labelTerms] = await Promise.all([
          getAdminTaxonomy("product-types"),
          getAdminTaxonomy("categories"),
          getAdminTaxonomy("labels"),
        ]);
        if (!cancelled) {
          setProductTypes(typeTerms);
          setCategories(categoryTerms);
          setLabels(labelTerms);
        }
      } catch {
        if (!cancelled) {
          setProductTypes([]);
          setCategories([]);
          setLabels([]);
        }
      }
    }
    loadTaxonomy();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const params = filtersToParams(filters);
    const query = params.toString();
    window.history.replaceState(
      {},
      "",
      `${window.location.pathname}${query ? `?${query}` : ""}`
    );
  }, [filters]);

  useEffect(() => {
    const visibleIds = new Set(products.map((product) => product.id));
    setSelectedIds((prev) => {
      const next = new Set(Array.from(prev).filter((id) => visibleIds.has(id)));
      return next.size === prev.size ? prev : next;
    });
  }, [products]);

  function updateFilters(next: Partial<AdminProductFilters>) {
    setFilters((prev) => ({ ...prev, ...next }));
  }

  function clearFilters() {
    setFilters({ ...DEFAULT_FILTERS });
  }

  function termName(terms: AdminTaxonomyTerm[], slug: string) {
    const term = terms.find((item) => item.slug === slug);
    return term?.name_en ?? slug;
  }

  const activeFilterChips = useMemo(() => {
    const chips: Array<{ key: string; label: string; remove: () => void }> = [];
    if (filters.q?.trim()) {
      chips.push({
        key: "q",
        label: t("productFilters.searchChip", { value: filters.q.trim() }),
        remove: () => updateFilters({ q: "" }),
      });
    }
    if (filters.status && filters.status !== "all") {
      chips.push({
        key: "status",
        label: filters.status === "active" ? t("active") : t("inactive"),
        remove: () => updateFilters({ status: "all" }),
      });
    }
    if (filters.media && filters.media !== "any") {
      const labelsByMedia: Record<string, string> = {
        ready: t("productFilters.mediaReady"),
        missing_image: t("productFilters.mediaMissingImage"),
        has_video: t("productFilters.mediaHasVideo"),
        missing_video: t("productFilters.mediaMissingVideo"),
      };
      chips.push({
        key: "media",
        label: labelsByMedia[filters.media] ?? filters.media,
        remove: () => updateFilters({ media: "any" }),
      });
    }
    if (filters.stock && filters.stock !== "any") {
      const labelsByStock: Record<string, string> = {
        in_stock: t("productFilters.stockInStock"),
        out_of_stock: t("productFilters.stockOutOfStock"),
        low: t("productFilters.stockLow"),
      };
      chips.push({
        key: "stock",
        label: labelsByStock[filters.stock] ?? filters.stock,
        remove: () => updateFilters({ stock: "any" }),
      });
    }
    if (filters.product_type) {
      chips.push({
        key: "product_type",
        label: t("productFilters.productTypeChip", { value: termName(productTypes, filters.product_type) }),
        remove: () => updateFilters({ product_type: "" }),
      });
    }
    if (filters.category) {
      chips.push({
        key: "category",
        label: t("productFilters.categoryChip", { value: termName(categories, filters.category) }),
        remove: () => updateFilters({ category: "" }),
      });
    }
    for (const label of filters.label ?? []) {
      chips.push({
        key: `label-${label}`,
        label: t("productFilters.labelChip", { value: termName(labels, label) }),
        remove: () => updateFilters({ label: (filters.label ?? []).filter((item) => item !== label) }),
      });
    }
    if (filters.featured !== null && filters.featured !== undefined) {
      chips.push({
        key: "featured",
        label: filters.featured ? t("productFilters.featuredOnly") : t("productFilters.notFeatured"),
        remove: () => updateFilters({ featured: null }),
      });
    }
    if (filters.discount && filters.discount !== "any") {
      const labelsByDiscount: Record<string, string> = {
        active: t("productFilters.discountActive"),
        scheduled: t("productFilters.discountScheduled"),
        none: t("productFilters.discountNone"),
      };
      chips.push({
        key: "discount",
        label: labelsByDiscount[filters.discount] ?? filters.discount,
        remove: () => updateFilters({ discount: "any" }),
      });
    }
    if (filters.inventory_mode) {
      const labelsByInventory: Record<string, string> = {
        legacy: t("productFilters.inventoryLegacy"),
        fallback: t("productFilters.inventoryFallback"),
        ledger_managed: t("productFilters.inventoryLedgerManaged"),
      };
      chips.push({
        key: "inventory_mode",
        label: labelsByInventory[filters.inventory_mode] ?? filters.inventory_mode,
        remove: () => updateFilters({ inventory_mode: "" }),
      });
    }
    if (filters.recipe_status) {
      const labelsByRecipe: Record<string, string> = {
        active: t("productFilters.recipeActive"),
        missing: t("productFilters.recipeMissing"),
        draft: t("productFilters.recipeDraft"),
        archived: t("productFilters.recipeArchived"),
      };
      chips.push({
        key: "recipe_status",
        label: labelsByRecipe[filters.recipe_status] ?? filters.recipe_status,
        remove: () => updateFilters({ recipe_status: "" }),
      });
    }
    if (filters.has_inventory_exceptions !== null && filters.has_inventory_exceptions !== undefined) {
      chips.push({
        key: "has_inventory_exceptions",
        label: filters.has_inventory_exceptions
          ? t("productFilters.hasExceptions")
          : t("productFilters.noExceptions"),
        remove: () => updateFilters({ has_inventory_exceptions: null }),
      });
    }
    return chips;
  }, [categories, filters, labels, productTypes, t]);

  async function toggleActive(product: AdminProductResponse) {
    const previousActive = product.is_active;
    setConfirmDeleteId(null);
    if (!previousActive && product.images.length === 0) {
      setError(t("mediaRequiredToActivate"));
      return;
    }
    setTogglingId(product.id);

    // Optimistic update
    setProducts((prev) =>
      prev.map((p) =>
        p.id === product.id ? { ...p, is_active: !p.is_active } : p
      )
    );

    try {
      const updated = await updateProduct(product.id, {
        is_active: !previousActive,
      });
      setProducts((prev) =>
        prev.map((p) => (p.id === updated.id ? updated : p))
      );
      showSuccess(tCommon("saved"));
      void loadProducts();
    } catch (err) {
      // Rollback
      setProducts((prev) =>
        prev.map((p) =>
          p.id === product.id ? { ...p, is_active: previousActive } : p
        )
      );
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("errors.updateProduct"));
    } finally {
      setTogglingId(null);
    }
  }

  async function confirmDelete(product: AdminProductResponse) {
    setDeletingId(product.id);
    setError(null);
    try {
      const updated = await deleteProduct(product.id);
      setProducts((prev) =>
        prev.map((p) => (p.id === updated.id ? updated : p))
      );
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(product.id);
        return next;
      });
      setConfirmDeleteId(null);
      showSuccess(t("productDeleted"));
      void loadProducts();
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("errors.updateProduct"));
    } finally {
      setDeletingId(null);
    }
  }

  function showSuccess(message: string) {
    if (successTimerRef.current) clearTimeout(successTimerRef.current);
    setSuccessMessage(message);
    setSuccessNoticeId((current) => current + 1);
    successTimerRef.current = setTimeout(() => {
      setSuccessMessage(null);
    }, 3200);
  }

  function dismissSuccess() {
    setSuccessMessage(null);
    if (successTimerRef.current) clearTimeout(successTimerRef.current);
  }

  function toggleSelected(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    setSelectedIds((prev) =>
      prev.size === products.length ? new Set() : new Set(products.map((p) => p.id))
    );
  }

  const allSelected = products.length > 0 && selectedIds.size === products.length;

  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = selectedIds.size > 0 && !allSelected;
    }
  }, [selectedIds, allSelected]);

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-heading text-2xl font-semibold text-charcoal">
              {t("products")}
            </h1>
          </div>
        </div>
        <Link
          href="/admin/products/new"
          className="inline-flex h-10 items-center justify-center rounded-brand bg-charcoal px-4 text-sm font-medium text-cream transition-colors hover:bg-charcoal/90"
        >
          {t("createProduct")}
        </Link>
      </div>

      {successMessage && (
        <SaveConfirmation
          key={successNoticeId}
          message={successMessage}
          onDismiss={dismissSuccess}
          dismissLabel={t("dismissSuccess")}
        />
      )}

      {error && (
        <div className="mb-6 rounded-brand border border-error/20 bg-error/10 p-4 text-sm text-error">
          {error}
        </div>
      )}

      <section className="mb-4 rounded-brand border border-admin-border/60 bg-admin-surface p-4">
        <div className="grid gap-3 lg:grid-cols-[minmax(220px,1fr)_auto_auto] lg:items-end">
          <div>
            <label htmlFor="admin-product-search" className="mb-1.5 block text-sm font-medium text-admin-text">
              {t("productFilters.searchLabel")}
            </label>
            <input
              id="admin-product-search"
              type="search"
              value={filters.q ?? ""}
              onChange={(event) => updateFilters({ q: event.target.value })}
              placeholder={t("productFilters.searchPlaceholder")}
              className="h-10 w-full rounded-brand border border-admin-border bg-admin-surface px-3 text-sm text-admin-text outline-none transition focus:border-admin-focus focus:ring-2 focus:ring-admin-focus/20"
            />
          </div>

          <div>
            <span className="mb-1.5 block text-sm font-medium text-admin-text">
              {t("productFilters.statusLabel")}
            </span>
            <div className="inline-flex h-10 overflow-hidden rounded-brand border border-admin-border bg-admin-surface text-sm">
              {(["all", "active", "inactive"] as AdminProductStatusFilter[]).map((value) => (
                <button
                  key={value}
                  type="button"
                  aria-pressed={filters.status === value}
                  onClick={() => updateFilters({ status: value })}
                  className={`px-3 font-medium transition ${
                    filters.status === value
                      ? "bg-charcoal text-cream"
                      : "text-admin-muted hover:bg-admin-surface-muted/60 hover:text-admin-text"
                  }`}
                >
                  {value === "all" ? t("all") : value === "active" ? t("active") : t("inactive")}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="admin-product-sort" className="mb-1.5 block text-sm font-medium text-admin-text">
              {t("productFilters.sortLabel")}
            </label>
            <select
              id="admin-product-sort"
              value={filters.sort ?? "created_desc"}
              onChange={(event) => updateFilters({ sort: event.target.value as AdminProductSort })}
              className="h-10 rounded-brand border border-admin-border bg-admin-surface px-3 text-sm text-admin-text outline-none transition focus:border-admin-focus focus:ring-2 focus:ring-admin-focus/20"
            >
              <option value="created_desc">{t("productFilters.sortCreatedDesc")}</option>
              <option value="updated_desc">{t("productFilters.sortUpdatedDesc")}</option>
              <option value="name_asc">{t("productFilters.sortNameAsc")}</option>
              <option value="price_asc">{t("productFilters.sortPriceAsc")}</option>
              <option value="price_desc">{t("productFilters.sortPriceDesc")}</option>
              <option value="stock_asc">{t("productFilters.sortStockAsc")}</option>
            </select>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            type="button"
            aria-pressed={filters.media === "missing_image"}
            onClick={() => updateFilters({ media: filters.media === "missing_image" ? "any" : "missing_image" })}
            className={`h-9 rounded-brand border px-3 text-sm font-medium transition ${
              filters.media === "missing_image"
                ? "border-warning bg-warning/10 text-admin-text"
                : "border-admin-border text-admin-muted hover:bg-admin-surface-muted/60 hover:text-admin-text"
            }`}
          >
            {t("productFilters.mediaMissingImage")}
          </button>
          <button
            type="button"
            aria-pressed={filters.stock === "low"}
            onClick={() => updateFilters({ stock: filters.stock === "low" ? "any" : "low" })}
            className={`h-9 rounded-brand border px-3 text-sm font-medium transition ${
              filters.stock === "low"
                ? "border-warning bg-warning/10 text-admin-text"
                : "border-admin-border text-admin-muted hover:bg-admin-surface-muted/60 hover:text-admin-text"
            }`}
          >
            {t("productFilters.stockLow")}
          </button>
          <button
            type="button"
            aria-pressed={filters.discount === "active"}
            onClick={() => updateFilters({ discount: filters.discount === "active" ? "any" : "active" })}
            className={`h-9 rounded-brand border px-3 text-sm font-medium transition ${
              filters.discount === "active"
                ? "border-muted-gold bg-muted-gold/10 text-admin-text"
                : "border-admin-border text-admin-muted hover:bg-admin-surface-muted/60 hover:text-admin-text"
            }`}
          >
            {t("productFilters.discountActive")}
          </button>
          <button
            type="button"
            onClick={() => setShowAdvancedFilters((value) => !value)}
            className="h-9 rounded-brand border border-admin-border px-3 text-sm font-medium text-admin-text transition hover:bg-admin-surface-muted/60"
          >
            {showAdvancedFilters ? t("productFilters.hideFilters") : t("productFilters.moreFilters")}
            {activeFilterChips.length > 0 && (
              <span className="ml-2 rounded-pill bg-charcoal px-2 py-0.5 text-xs text-cream">
                {activeFilterChips.length}
              </span>
            )}
          </button>
          {activeFilterChips.length > 0 && (
            <button
              type="button"
              onClick={clearFilters}
              className="h-9 rounded-brand px-3 text-sm font-medium text-admin-muted transition hover:bg-admin-surface-muted/60 hover:text-admin-text"
            >
              {t("productFilters.clearAll")}
            </button>
          )}
        </div>

        {showAdvancedFilters && (
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <label htmlFor="admin-filter-product-type" className="mb-1.5 block text-sm font-medium text-admin-text">
                {t("productFilters.productTypeLabel")}
              </label>
              <select
                id="admin-filter-product-type"
                value={filters.product_type ?? ""}
                onChange={(event) => updateFilters({ product_type: event.target.value })}
                className="h-10 w-full rounded-brand border border-admin-border bg-admin-surface px-3 text-sm text-admin-text"
              >
                <option value="">{t("productFilters.any")}</option>
                {productTypes.map((term) => (
                  <option key={term.slug} value={term.slug}>{term.name_en}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="admin-filter-category" className="mb-1.5 block text-sm font-medium text-admin-text">
                {t("category")}
              </label>
              <select
                id="admin-filter-category"
                value={filters.category ?? ""}
                onChange={(event) => updateFilters({ category: event.target.value })}
                className="h-10 w-full rounded-brand border border-admin-border bg-admin-surface px-3 text-sm text-admin-text"
              >
                <option value="">{t("productFilters.any")}</option>
                {categories.map((term) => (
                  <option key={term.slug} value={term.slug}>{term.name_en}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="admin-filter-label" className="mb-1.5 block text-sm font-medium text-admin-text">
                {t("productFilters.labelLabel")}
              </label>
              <select
                id="admin-filter-label"
                value={(filters.label ?? [])[0] ?? ""}
                onChange={(event) => updateFilters({ label: event.target.value ? [event.target.value] : [] })}
                className="h-10 w-full rounded-brand border border-admin-border bg-admin-surface px-3 text-sm text-admin-text"
              >
                <option value="">{t("productFilters.any")}</option>
                {labels.map((term) => (
                  <option key={term.slug} value={term.slug}>{term.name_en}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="admin-filter-media" className="mb-1.5 block text-sm font-medium text-admin-text">
                {t("media")}
              </label>
              <select
                id="admin-filter-media"
                value={filters.media ?? "any"}
                onChange={(event) => updateFilters({ media: event.target.value as AdminProductMediaFilter })}
                className="h-10 w-full rounded-brand border border-admin-border bg-admin-surface px-3 text-sm text-admin-text"
              >
                <option value="any">{t("productFilters.any")}</option>
                <option value="ready">{t("productFilters.mediaReady")}</option>
                <option value="missing_image">{t("productFilters.mediaMissingImage")}</option>
                <option value="has_video">{t("productFilters.mediaHasVideo")}</option>
                <option value="missing_video">{t("productFilters.mediaMissingVideo")}</option>
              </select>
            </div>
            <div>
              <label htmlFor="admin-filter-stock" className="mb-1.5 block text-sm font-medium text-admin-text">
                {t("stock")}
              </label>
              <select
                id="admin-filter-stock"
                value={filters.stock ?? "any"}
                onChange={(event) => updateFilters({ stock: event.target.value as AdminProductStockFilter })}
                className="h-10 w-full rounded-brand border border-admin-border bg-admin-surface px-3 text-sm text-admin-text"
              >
                <option value="any">{t("productFilters.any")}</option>
                <option value="in_stock">{t("productFilters.stockInStock")}</option>
                <option value="out_of_stock">{t("productFilters.stockOutOfStock")}</option>
                <option value="low">{t("productFilters.stockLow")}</option>
              </select>
            </div>
            <div>
              <label htmlFor="admin-filter-featured" className="mb-1.5 block text-sm font-medium text-admin-text">
                {t("productFilters.featuredLabel")}
              </label>
              <select
                id="admin-filter-featured"
                value={filters.featured === null || filters.featured === undefined ? "" : String(filters.featured)}
                onChange={(event) => updateFilters({ featured: booleanParam(event.target.value || null) })}
                className="h-10 w-full rounded-brand border border-admin-border bg-admin-surface px-3 text-sm text-admin-text"
              >
                <option value="">{t("productFilters.any")}</option>
                <option value="true">{t("productFilters.featuredOnly")}</option>
                <option value="false">{t("productFilters.notFeatured")}</option>
              </select>
            </div>
            <div>
              <label htmlFor="admin-filter-discount" className="mb-1.5 block text-sm font-medium text-admin-text">
                {t("productFilters.discountLabel")}
              </label>
              <select
                id="admin-filter-discount"
                value={filters.discount ?? "any"}
                onChange={(event) => updateFilters({ discount: event.target.value as AdminProductDiscountFilter })}
                className="h-10 w-full rounded-brand border border-admin-border bg-admin-surface px-3 text-sm text-admin-text"
              >
                <option value="any">{t("productFilters.any")}</option>
                <option value="active">{t("productFilters.discountActive")}</option>
                <option value="scheduled">{t("productFilters.discountScheduled")}</option>
                <option value="none">{t("productFilters.discountNone")}</option>
              </select>
            </div>
            <div>
              <label htmlFor="admin-filter-inventory" className="mb-1.5 block text-sm font-medium text-admin-text">
                {t("productFilters.inventoryLabel")}
              </label>
              <select
                id="admin-filter-inventory"
                value={filters.inventory_mode ?? ""}
                onChange={(event) => updateFilters({ inventory_mode: event.target.value as AdminProductInventoryModeFilter | "" })}
                className="h-10 w-full rounded-brand border border-admin-border bg-admin-surface px-3 text-sm text-admin-text"
              >
                <option value="">{t("productFilters.any")}</option>
                <option value="legacy">{t("productFilters.inventoryLegacy")}</option>
                <option value="fallback">{t("productFilters.inventoryFallback")}</option>
                <option value="ledger_managed">{t("productFilters.inventoryLedgerManaged")}</option>
              </select>
            </div>
            <div>
              <label htmlFor="admin-filter-recipe" className="mb-1.5 block text-sm font-medium text-admin-text">
                {t("productFilters.recipeLabel")}
              </label>
              <select
                id="admin-filter-recipe"
                value={filters.recipe_status ?? ""}
                onChange={(event) => updateFilters({ recipe_status: event.target.value as AdminProductRecipeStatusFilter | "" })}
                className="h-10 w-full rounded-brand border border-admin-border bg-admin-surface px-3 text-sm text-admin-text"
              >
                <option value="">{t("productFilters.any")}</option>
                <option value="active">{t("productFilters.recipeActive")}</option>
                <option value="missing">{t("productFilters.recipeMissing")}</option>
                <option value="draft">{t("productFilters.recipeDraft")}</option>
                <option value="archived">{t("productFilters.recipeArchived")}</option>
              </select>
            </div>
            <div>
              <label htmlFor="admin-filter-exceptions" className="mb-1.5 block text-sm font-medium text-admin-text">
                {t("productFilters.exceptionsLabel")}
              </label>
              <select
                id="admin-filter-exceptions"
                value={
                  filters.has_inventory_exceptions === null || filters.has_inventory_exceptions === undefined
                    ? ""
                    : String(filters.has_inventory_exceptions)
                }
                onChange={(event) => updateFilters({ has_inventory_exceptions: booleanParam(event.target.value || null) })}
                className="h-10 w-full rounded-brand border border-admin-border bg-admin-surface px-3 text-sm text-admin-text"
              >
                <option value="">{t("productFilters.any")}</option>
                <option value="true">{t("productFilters.hasExceptions")}</option>
                <option value="false">{t("productFilters.noExceptions")}</option>
              </select>
            </div>
          </div>
        )}

        {activeFilterChips.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {activeFilterChips.map((chip) => (
              <button
                key={chip.key}
                type="button"
                onClick={chip.remove}
                className="inline-flex h-8 items-center gap-2 rounded-pill border border-admin-border bg-admin-surface-muted/40 px-3 text-xs font-medium text-admin-text hover:bg-admin-surface-muted/70"
                aria-label={t("productFilters.removeFilter", { name: chip.label })}
              >
                {chip.label}
                <span aria-hidden="true" className="text-admin-muted">x</span>
              </button>
            ))}
          </div>
        )}

        <div className="mt-3 text-sm text-admin-muted" role="status">
          {t("productFilters.results", { shown: products.length, total: totalProducts })}
        </div>
      </section>

      {selectedIds.size > 0 && (
        <ProductBulkDiscountBar
          selectedIds={Array.from(selectedIds)}
          onDone={() => {
            loadProducts();
          }}
        />
      )}

      <div className="space-y-3 md:hidden">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-brand border border-admin-border/60 bg-admin-surface p-4">
              <Skeleton className="h-5 w-40" />
              <div className="mt-4 grid grid-cols-2 gap-3">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-4 w-28" />
                <Skeleton className="h-4 w-24" />
              </div>
            </div>
          ))
        ) : products.length === 0 ? (
          <div className="rounded-brand border border-admin-border/60 bg-admin-surface px-4 py-8 text-center text-sm text-admin-muted">
            {t("noProducts")}
          </div>
        ) : (
          products.map((product) => (
            <article key={product.id} className="rounded-brand border border-admin-border/60 bg-admin-surface p-4 text-sm text-admin-muted">
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  checked={selectedIds.has(product.id)}
                  onChange={() => toggleSelected(product.id)}
                  aria-label={product.name_en}
                  className="mt-1"
                />
                <div className="min-w-0 flex-1">
                  <h2 className="font-heading text-lg font-semibold text-admin-text">{product.name_en}</h2>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Badge variant={product.is_active ? "success" : "warning"}>
                      {product.is_active ? t("active") : t("inactive")}
                    </Badge>
                    {product.images.length > 0 ? (
                      <Badge variant="success">{t("mediaReady")}</Badge>
                    ) : (
                      <Badge variant="warning">{t("mediaMissing")}</Badge>
                    )}
                  </div>
                </div>
              </div>

              <dl className="mt-4 grid grid-cols-2 gap-3">
                <div>
                  <dt className="text-xs font-semibold uppercase text-admin-muted">{t("category")}</dt>
                  <dd className="mt-1 text-admin-text">{product.category || "-"}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase text-admin-muted">{t("price")}</dt>
                  <dd className="mt-1 text-admin-text">{formatPrice(product.price_cents)}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase text-admin-muted">{t("stock")}</dt>
                  <dd className="mt-1 text-admin-text">{product.stock}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase text-admin-muted">{t("inventoryColumn")}</dt>
                  <dd className="mt-1 text-admin-text">{(product.inventory_mode ?? "legacy").replaceAll("_", " ")}</dd>
                </div>
              </dl>

              <div className="mt-4 rounded-brand border border-admin-border/50 bg-admin-surface-muted/35 p-3 text-xs text-admin-muted">
                <div className="flex flex-col gap-1">
                  <span>{t("recipeStatus")}: {product.active_recipe_status ?? "missing"}</span>
                  <span>{t("stockSource")}: {(product.stock_source ?? "product_stock").replaceAll("_", " ")}</span>
                  {product.latest_batch_number && (
                    <Link href={`/admin/inventory/batches?product_id=${product.id}`} className="font-medium text-admin-text underline-offset-2 hover:underline">
                      {product.latest_batch_number}
                    </Link>
                  )}
                  {Boolean(product.inventory_exception_count) && (
                    <Link href={`/admin/inventory/valuation/exceptions?target_type=product&target_id=${product.id}`} className="font-medium text-warning underline-offset-2 hover:underline">
                      {t("inventoryExceptions", { count: product.inventory_exception_count ?? 0 })}
                    </Link>
                  )}
                </div>
              </div>

              <div className="mt-4 flex flex-wrap items-center gap-2">
                <Link
                  href={`/admin/products/${product.id}/edit`}
                  className="inline-flex h-9 items-center justify-center rounded-brand border border-admin-border/60 px-3 text-sm font-medium text-admin-text hover:bg-admin-surface-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-admin-focus focus-visible:ring-offset-2 focus-visible:ring-offset-admin-surface"
                >
                  {tCommon("edit")}
                </Link>
                <Button
                  variant="secondary"
                  size="sm"
                  isLoading={togglingId === product.id}
                  disabled={!product.is_active && product.images.length === 0}
                  onClick={() => toggleActive(product)}
                >
                  {product.is_active ? t("deactivate") : t("activate")}
                </Button>
                {confirmDeleteId === product.id ? (
                  <>
                    <span className="basis-full text-xs text-admin-muted sm:basis-auto">
                      {t("deleteProductConfirm", { name: product.name_en })}
                    </span>
                    <DeleteIconButton
                      label={t("confirmDeleteProduct")}
                      isLoading={deletingId === product.id}
                      onClick={() => confirmDelete(product)}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setConfirmDeleteId(null)}
                    >
                      {tCommon("cancel")}
                    </Button>
                  </>
                ) : (
                  <DeleteIconButton
                    label={t("deleteProduct")}
                    onClick={() => setConfirmDeleteId(product.id)}
                  />
                )}
              </div>
            </article>
          ))
        )}
      </div>

      <div className="hidden overflow-x-auto rounded-brand border border-champagne-beige bg-cream md:block">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-champagne-beige bg-champagne-beige/30">
              <th className="px-4 py-3">
                <input
                  ref={selectAllRef}
                  type="checkbox"
                  checked={allSelected}
                  onChange={toggleSelectAll}
                  aria-label={t("promotions.selectAll")}
                />
              </th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("name")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("category")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("price")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("stock")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("inventoryColumn")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("media")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("status")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("actions")}</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <tr key={i} className="border-b border-champagne-beige/50">
                  <td className="px-4 py-3"><Skeleton className="h-4 w-4" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-32" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-20" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-16" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-10" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-5 w-28" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-5 w-16" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-5 w-16" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-8 w-24" /></td>
                </tr>
              ))
            ) : products.length === 0 ? (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-soft-brown">
                  {t("noProducts")}
                </td>
              </tr>
            ) : (
              products.map((product) => (
                <tr
                  key={product.id}
                  className="border-b border-champagne-beige/50 last:border-0"
                >
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(product.id)}
                      onChange={() => toggleSelected(product.id)}
                      aria-label={product.name_en}
                    />
                  </td>
                  <td className="px-4 py-3 font-medium text-charcoal">
                    {product.name_en}
                  </td>
                  <td className="px-4 py-3 text-soft-brown">
                    {product.category || "—"}
                  </td>
                  <td className="px-4 py-3 text-soft-brown">
                    {formatPrice(product.price_cents)}
                  </td>
                  <td className="px-4 py-3 text-soft-brown">{product.stock}</td>
                  <td className="px-4 py-3 text-xs text-soft-brown">
                    <div className="flex flex-col gap-1">
                      <span className="inline-flex w-fit rounded-pill bg-champagne-beige/60 px-2 py-0.5 font-medium capitalize text-soft-brown">
                        {(product.inventory_mode ?? "legacy").replaceAll("_", " ")}
                      </span>
                      <span>{t("recipeStatus")}: {product.active_recipe_status ?? "missing"}</span>
                      <span>{t("stockSource")}: {(product.stock_source ?? "product_stock").replaceAll("_", " ")}</span>
                      {product.latest_batch_number && (
                        <Link href={`/admin/inventory/batches?product_id=${product.id}`} className="font-medium text-charcoal underline-offset-2 hover:underline">
                          {product.latest_batch_number}
                        </Link>
                      )}
                      {Boolean(product.inventory_exception_count) && (
                        <Link href={`/admin/inventory/valuation/exceptions?target_type=product&target_id=${product.id}`} className="font-medium text-warning underline-offset-2 hover:underline">
                          {t("inventoryExceptions", { count: product.inventory_exception_count ?? 0 })}
                        </Link>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {product.images.length > 0 ? (
                      <Badge variant="success">{t("mediaReady")}</Badge>
                    ) : (
                      <Badge variant="warning">{t("mediaMissing")}</Badge>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={product.is_active ? "success" : "warning"}>
                      {product.is_active ? t("active") : t("inactive")}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Link
                        href={`/admin/products/${product.id}/edit`}
                        className="inline-flex h-8 items-center justify-center rounded-brand px-3 text-xs font-medium text-soft-brown hover:bg-champagne-beige/50 hover:text-charcoal"
                      >
                        {tCommon("edit")}
                      </Link>
                      <Button
                        variant="secondary"
                        size="sm"
                        isLoading={togglingId === product.id}
                        disabled={!product.is_active && product.images.length === 0}
                        onClick={() => toggleActive(product)}
                      >
                        {product.is_active ? t("deactivate") : t("activate")}
                      </Button>
                      {confirmDeleteId === product.id ? (
                        <>
                          <span className="max-w-40 text-xs text-soft-brown">
                            {t("deleteProductConfirm", { name: product.name_en })}
                          </span>
                          <DeleteIconButton
                            label={t("confirmDeleteProduct")}
                            isLoading={deletingId === product.id}
                            onClick={() => confirmDelete(product)}
                          />
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => setConfirmDeleteId(null)}
                          >
                            {tCommon("cancel")}
                          </Button>
                        </>
                      ) : (
                        <DeleteIconButton
                          label={t("deleteProduct")}
                          onClick={() => setConfirmDeleteId(product.id)}
                        />
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* CSV Import Format Reference */}
      <details className="mt-8 rounded-brand border border-champagne-beige bg-cream">
        <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-charcoal hover:bg-champagne-beige/30">
          {t("csvReference")}
        </summary>
        <div className="border-t border-champagne-beige px-4 py-4 text-sm text-soft-brown">
          <p className="mb-3">
            {t("csvImportDescription", { endpoint: "POST /v1/admin/products/import" })}
          </p>
          <p className="mb-2 font-medium text-charcoal">{t("requiredColumns")}</p>
          <ul className="mb-3 ml-4 list-disc space-y-1">
            <li><code className="text-xs">id</code> - {t("csvColumnId")} (<code className="text-xs">lavender-dreams-300ml</code>)</li>
            <li><code className="text-xs">name_en</code> - {t("csvColumnNameEn")}</li>
            <li><code className="text-xs">price_cents</code> - {t("csvColumnPrice")}</li>
            <li><code className="text-xs">category</code> - {t("csvColumnCategory")}</li>
            <li><code className="text-xs">stock</code> - {t("csvColumnStock")}</li>
          </ul>
          <p className="mb-2 font-medium text-charcoal">{t("optionalBilingualColumns")}</p>
          <ul className="mb-3 ml-4 list-disc space-y-1">
            <li><code className="text-xs">name_bg</code> - {t("csvColumnNameBg")}</li>
            <li><code className="text-xs">description_en</code> - {t("csvColumnDescriptionEn")}</li>
            <li><code className="text-xs">description_bg</code> - {t("csvColumnDescriptionBg")}</li>
            <li><code className="text-xs">materials</code>, <code className="text-xs">days_to_craft</code>, <code className="text-xs">image_url</code>, <code className="text-xs">is_featured</code>, <code className="text-xs">is_active</code>, <code className="text-xs">weight_grams</code></li>
            <li><code className="text-xs">safety_warnings_en</code>, <code className="text-xs">safety_warnings_bg</code>, <code className="text-xs">care_instructions_en</code>, <code className="text-xs">care_instructions_bg</code></li>
          </ul>
          <p className="mb-2 font-medium text-charcoal">{t("example")}</p>
          <pre className="overflow-x-auto rounded bg-charcoal/5 p-3 text-xs leading-relaxed">
{`id,name_en,name_bg,description_en,description_bg,price_cents,category,stock,weight_grams,is_active,safety_warnings_en,care_instructions_en
lavender-dreams-300ml,Lavender Dreams,Лавандулов сън,Hand-poured soy candle,Ръчно излята соева свещ,3200,Floral,24,300,true,Never leave unattended.,Trim wick before use.
midnight-amber-300ml,Midnight Amber,Полунощен кехлибар,Warm amber and sandalwood,Топъл кехлибар и сандалово дърво,4500,Woody,12,450,true,Never leave unattended.,Use on a heat-resistant surface.`}
          </pre>
          <p className="mt-3 text-xs text-soft-brown/70">
            {t("csvFallbackNote")}
          </p>
        </div>
      </details>
    </div>
  );
}
