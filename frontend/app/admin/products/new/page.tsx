"use client";

import { createProduct } from "@/lib/api";
import { ProductForm, type ProductFormData } from "@/components/admin/ProductForm";

export default function CreateProductPage() {
  async function handleSubmit(data: ProductFormData) {
    await createProduct({
      id: data.id,
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

  return (
    <div>
      <div className="mb-8">
        <h1 className="font-heading text-2xl font-semibold text-charcoal">
          Create Product
        </h1>
        <p className="mt-1 text-sm text-soft-brown">
          Add a new product to your catalog
        </p>
      </div>

      <div className="max-w-3xl rounded-brand border border-champagne-beige bg-cream p-6">
        <ProductForm onSubmit={handleSubmit} submitLabel="Create Product" />
      </div>
    </div>
  );
}
