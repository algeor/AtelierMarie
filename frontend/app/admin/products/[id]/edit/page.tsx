"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getAdminProduct, updateProduct } from "@/lib/api";
import { ProductForm, type ProductFormData } from "@/components/admin/ProductForm";
import { Skeleton } from "@/components/ui/Skeleton";
import type { ProductResponse } from "@/lib/types";

export default function EditProductPage() {
  const params = useParams();
  const productId = params.id as string;
  const [product, setProduct] = useState<ProductResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAdminProduct(productId)
      .then(setProduct)
      .catch((err) => setError(err.message || "Failed to load product"))
      .finally(() => setIsLoading(false));
  }, [productId]);

  async function handleSubmit(data: ProductFormData) {
    await updateProduct(productId, {
      name: data.name,
      description: data.description || null,
      materials: data.materials || null,
      days_to_craft: data.days_to_craft,
      price_cents: data.price_cents,
      category: data.category,
      image_url: data.image_url || null,
      stock: data.stock,
      is_featured: data.is_featured,
    });
  }

  if (isLoading) {
    return (
      <div>
        <Skeleton className="mb-2 h-8 w-48" />
        <Skeleton className="mb-8 h-4 w-64" />
        <div className="max-w-3xl space-y-4 rounded-brand border border-champagne-beige bg-cream p-6">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-brand border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        {error}
      </div>
    );
  }

  if (!product) return null;

  return (
    <div>
      <div className="mb-8">
        <h1 className="font-heading text-2xl font-semibold text-charcoal">
          Edit Product
        </h1>
        <p className="mt-1 text-sm text-soft-brown">
          Update {product.name}
        </p>
      </div>

      <div className="max-w-3xl rounded-brand border border-champagne-beige bg-cream p-6">
        <ProductForm
          product={product}
          onSubmit={handleSubmit}
          submitLabel="Save Changes"
        />
      </div>
    </div>
  );
}
