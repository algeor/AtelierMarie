"use client";

import { useEffect, useState, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { getAdminProducts, updateProduct } from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { useLocalizedError } from "@/lib/useLocalizedError";
import { formatPrice } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import type { AdminProductResponse } from "@/lib/types";

export default function AdminProductsPage() {
  const t = useTranslations("admin");
  const tCommon = useTranslations("common");
  const getLocalizedError = useLocalizedError();
  const searchParams = useSearchParams();
  const [products, setProducts] = useState<AdminProductResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const successTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Show success banner from query param
  useEffect(() => {
    const success = searchParams.get("success");
    const messages: Record<string, string> = {
      created: t("productCreated"),
      updated: t("productUpdated"),
    };
    if (success && messages[success]) {
      setSuccessMessage(messages[success]);
      // Strip param from URL to prevent re-flash on refresh
      window.history.replaceState({}, "", window.location.pathname);
      // Auto-dismiss after 5 seconds
      successTimerRef.current = setTimeout(() => {
        setSuccessMessage(null);
      }, 5000);
    }
    return () => {
      if (successTimerRef.current) clearTimeout(successTimerRef.current);
    };
  }, [searchParams, t]);

  useEffect(() => {
    loadProducts();
  }, []);

  async function loadProducts() {
    try {
      setIsLoading(true);
      const data = await getAdminProducts(1, 100);
      setProducts(data.products);
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("errors.loadProducts"));
    } finally {
      setIsLoading(false);
    }
  }

  async function toggleActive(product: AdminProductResponse) {
    const previousActive = product.is_active;
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

  function dismissSuccess() {
    setSuccessMessage(null);
    if (successTimerRef.current) clearTimeout(successTimerRef.current);
  }

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="font-heading text-2xl font-semibold text-charcoal">
            {t("products")}
          </h1>
          <p className="mt-1 text-sm text-soft-brown">
            {t("manageProducts")}
          </p>
        </div>
        <Link
          href="/admin/products/new"
          className="inline-flex h-10 items-center justify-center rounded-brand bg-charcoal px-4 text-sm font-medium text-cream transition-colors hover:bg-charcoal/90"
        >
          {t("createProduct")}
        </Link>
      </div>

      {successMessage && (
        <div className="mb-6 flex items-center justify-between rounded-brand border border-green-200 bg-green-50 p-4 text-sm text-green-700">
          <span>{successMessage}</span>
          <button
            onClick={dismissSuccess}
            className="ml-4 text-green-500 hover:text-green-700"
            aria-label={t("dismissSuccess")}
          >
            ✕
          </button>
        </div>
      )}

      {error && (
        <div className="mb-6 rounded-brand border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="overflow-x-auto rounded-brand border border-champagne-beige bg-cream">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-champagne-beige bg-champagne-beige/30">
              <th className="px-4 py-3 font-medium text-charcoal">{t("name")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("category")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("price")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("stock")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("status")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("actions")}</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <tr key={i} className="border-b border-champagne-beige/50">
                  <td className="px-4 py-3"><Skeleton className="h-4 w-32" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-20" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-16" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-10" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-5 w-16" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-8 w-24" /></td>
                </tr>
              ))
            ) : products.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-soft-brown">
                  {t("noProducts")}
                </td>
              </tr>
            ) : (
              products.map((product) => (
                <tr
                  key={product.id}
                  className="border-b border-champagne-beige/50 last:border-0"
                >
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
                        onClick={() => toggleActive(product)}
                      >
                        {product.is_active ? t("deactivate") : t("activate")}
                      </Button>
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
            <li><code className="text-xs">materials</code>, <code className="text-xs">days_to_craft</code>, <code className="text-xs">image_url</code>, <code className="text-xs">is_featured</code></li>
          </ul>
          <p className="mb-2 font-medium text-charcoal">{t("example")}</p>
          <pre className="overflow-x-auto rounded bg-charcoal/5 p-3 text-xs leading-relaxed">
{`id,name_en,name_bg,description_en,description_bg,price_cents,category,stock
lavender-dreams-300ml,Lavender Dreams,Лавандулов сън,Hand-poured soy candle,Ръчно излята соева свещ,3200,Floral,24
midnight-amber-300ml,Midnight Amber,Полунощен кехлибар,Warm amber and sandalwood,Топъл кехлибар и сандалово дърво,4500,Woody,12`}
          </pre>
          <p className="mt-3 text-xs text-soft-brown/70">
            {t("csvFallbackNote")}
          </p>
        </div>
      </details>
    </div>
  );
}
