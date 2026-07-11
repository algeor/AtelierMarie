"use client";

import { useEffect, useState, useRef } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { getAdminProducts, updateProduct } from "@/lib/api";
import { formatPrice } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import type { AdminProductResponse } from "@/lib/types";

const SUCCESS_MESSAGES: Record<string, string> = {
  created: "Product created successfully",
  updated: "Product updated successfully",
};

export default function AdminProductsPage() {
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
    if (success && SUCCESS_MESSAGES[success]) {
      setSuccessMessage(SUCCESS_MESSAGES[success]);
      // Strip param from URL to prevent re-flash on refresh
      window.history.replaceState({}, "", "/admin/products");
      // Auto-dismiss after 5 seconds
      successTimerRef.current = setTimeout(() => {
        setSuccessMessage(null);
      }, 5000);
    }
    return () => {
      if (successTimerRef.current) clearTimeout(successTimerRef.current);
    };
  }, [searchParams]);

  useEffect(() => {
    loadProducts();
  }, []);

  async function loadProducts() {
    try {
      setIsLoading(true);
      const data = await getAdminProducts(1, 100);
      setProducts(data.products);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load products");
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
      setError(err instanceof Error ? err.message : "Failed to update product");
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
            Products
          </h1>
          <p className="mt-1 text-sm text-soft-brown">
            Manage your product catalog
          </p>
        </div>
        <Link
          href="/admin/products/new"
          className="inline-flex h-10 items-center justify-center rounded-brand bg-charcoal px-4 text-sm font-medium text-cream transition-colors hover:bg-charcoal/90"
        >
          Create Product
        </Link>
      </div>

      {successMessage && (
        <div className="mb-6 flex items-center justify-between rounded-brand border border-green-200 bg-green-50 p-4 text-sm text-green-700">
          <span>{successMessage}</span>
          <button
            onClick={dismissSuccess}
            className="ml-4 text-green-500 hover:text-green-700"
            aria-label="Dismiss success message"
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
              <th className="px-4 py-3 font-medium text-charcoal">Name</th>
              <th className="px-4 py-3 font-medium text-charcoal">Category</th>
              <th className="px-4 py-3 font-medium text-charcoal">Price</th>
              <th className="px-4 py-3 font-medium text-charcoal">Stock</th>
              <th className="px-4 py-3 font-medium text-charcoal">Status</th>
              <th className="px-4 py-3 font-medium text-charcoal">Actions</th>
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
                  No products found. Create your first product to get started.
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
                      {product.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Link
                        href={`/admin/products/${product.id}/edit`}
                        className="inline-flex h-8 items-center justify-center rounded-brand px-3 text-xs font-medium text-soft-brown hover:bg-champagne-beige/50 hover:text-charcoal"
                      >
                        Edit
                      </Link>
                      <Button
                        variant="secondary"
                        size="sm"
                        isLoading={togglingId === product.id}
                        onClick={() => toggleActive(product)}
                      >
                        {product.is_active ? "Deactivate" : "Activate"}
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
          CSV Import Format Reference
        </summary>
        <div className="border-t border-champagne-beige px-4 py-4 text-sm text-soft-brown">
          <p className="mb-3">
            Bulk import products via <code className="rounded bg-champagne-beige/50 px-1.5 py-0.5 text-xs">POST /v1/admin/products/import</code> with a CSV file.
          </p>
          <p className="mb-2 font-medium text-charcoal">Required columns:</p>
          <ul className="mb-3 ml-4 list-disc space-y-1">
            <li><code className="text-xs">id</code> — Product slug (e.g., <code className="text-xs">lavender-dreams-300ml</code>)</li>
            <li><code className="text-xs">name_en</code> — English product name</li>
            <li><code className="text-xs">price_cents</code> — Price in cents (integer)</li>
            <li><code className="text-xs">category</code> — Product category</li>
            <li><code className="text-xs">stock</code> — Stock quantity</li>
          </ul>
          <p className="mb-2 font-medium text-charcoal">Optional bilingual columns:</p>
          <ul className="mb-3 ml-4 list-disc space-y-1">
            <li><code className="text-xs">name_bg</code> — Bulgarian product name</li>
            <li><code className="text-xs">description_en</code> — English description</li>
            <li><code className="text-xs">description_bg</code> — Bulgarian description</li>
            <li><code className="text-xs">materials</code>, <code className="text-xs">days_to_craft</code>, <code className="text-xs">image_url</code>, <code className="text-xs">is_featured</code></li>
          </ul>
          <p className="mb-2 font-medium text-charcoal">Example:</p>
          <pre className="overflow-x-auto rounded bg-charcoal/5 p-3 text-xs leading-relaxed">
{`id,name_en,name_bg,description_en,description_bg,price_cents,category,stock
lavender-dreams-300ml,Lavender Dreams,Лавандулов сън,Hand-poured soy candle,Ръчно излята соева свещ,3200,Floral,24
midnight-amber-300ml,Midnight Amber,Полунощен кехлибар,Warm amber and sandalwood,Топъл кехлибар и сандалово дърво,4500,Woody,12`}
          </pre>
          <p className="mt-3 text-xs text-soft-brown/70">
            If Bulgarian columns are omitted, products are created with English content only. Fallback will display English when Bulgarian is unavailable.
          </p>
        </div>
      </details>
    </div>
  );
}
