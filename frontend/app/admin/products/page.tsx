"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getAdminProducts, updateProduct } from "@/lib/api";
import { formatPrice } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import type { ProductResponse } from "@/lib/types";

export default function AdminProductsPage() {
  const [products, setProducts] = useState<ProductResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);

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

  async function toggleActive(product: ProductResponse) {
    setTogglingId(product.id);
    try {
      const updated = await updateProduct(product.id, {
        is_active: !product.is_active,
      });
      setProducts((prev) =>
        prev.map((p) => (p.id === updated.id ? updated : p))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update product");
    } finally {
      setTogglingId(null);
    }
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
        <Link href="/admin/products/new">
          <Button>Create Product</Button>
        </Link>
      </div>

      {error && (
        <div className="mb-6 rounded-brand border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="overflow-hidden rounded-brand border border-champagne-beige bg-cream">
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
                    {product.name}
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
                      <Link href={`/admin/products/${product.id}/edit`}>
                        <Button variant="ghost" size="sm">
                          Edit
                        </Button>
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
    </div>
  );
}
