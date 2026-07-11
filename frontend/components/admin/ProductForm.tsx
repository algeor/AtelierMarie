"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import type { ProductResponse } from "@/lib/types";

const CATEGORIES = ["Floral", "Woody", "Fresh", "Gourmand", "Spicy", "Citrus"];

interface ProductFormProps {
  product?: ProductResponse;
  onSubmit: (data: ProductFormData) => Promise<void>;
  submitLabel: string;
}

export interface ProductFormData {
  id: string;
  name: string;
  description: string;
  materials: string;
  days_to_craft: number | null;
  price_cents: number;
  category: string;
  image_url: string;
  stock: number;
  is_featured: boolean;
}

/** Convert a EUR string (e.g., "32.50") to cents without floating-point errors. */
function eurToCents(value: string): number {
  const trimmed = value.trim();
  if (!trimmed) return 0;
  const parts = trimmed.split(".");
  const whole = parseInt(parts[0] || "0", 10);
  const fracStr = (parts[1] || "").padEnd(2, "0").slice(0, 2);
  const frac = parseInt(fracStr, 10);
  if (isNaN(whole) || isNaN(frac)) return 0;
  return whole * 100 + (whole < 0 ? -frac : frac);
}

export function ProductForm({ product, onSubmit, submitLabel }: ProductFormProps) {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Local string state for price input to avoid cursor jumping
  const [priceDisplay, setPriceDisplay] = useState(
    product?.price_cents ? (product.price_cents / 100).toFixed(2) : ""
  );

  const [formData, setFormData] = useState<ProductFormData>({
    id: product?.id ?? "",
    name: product?.name ?? "",
    description: product?.description ?? "",
    materials: product?.materials ?? "",
    days_to_craft: product?.days_to_craft ?? null,
    price_cents: product?.price_cents ?? 0,
    category: product?.category ?? "",
    image_url: product?.image_url ?? "",
    stock: product?.stock ?? 0,
    is_featured: product?.is_featured ?? false,
  });

  function validate(): boolean {
    const newErrors: Record<string, string> = {};
    if (!formData.name.trim()) newErrors.name = "Name is required";
    if (!formData.id.trim() && !product) newErrors.id = "Product ID is required";
    if (!product && formData.id.trim() && !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(formData.id)) {
      newErrors.id = "ID must be lowercase letters, numbers, and hyphens only";
    }
    if (formData.price_cents <= 0) newErrors.price_cents = "Price must be greater than 0";
    if (!formData.category) newErrors.category = "Category is required";
    if (formData.stock < 0) newErrors.stock = "Stock cannot be negative";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    setError(null);
    try {
      await onSubmit(formData);
      const successParam = product ? "updated" : "created";
      router.push(`/admin/products?success=${successParam}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save product");
    } finally {
      setIsSubmitting(false);
    }
  }

  function updateField<K extends keyof ProductFormData>(
    field: K,
    value: ProductFormData[K]
  ) {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <div className="rounded-brand border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid gap-6 sm:grid-cols-2">
        {!product && (
          <Input
            label="Product ID (slug)"
            placeholder="e.g., lavender-dreams-300ml"
            value={formData.id}
            onChange={(e) => updateField("id", e.target.value)}
            error={errors.id}
          />
        )}
        <Input
          label="Name"
          placeholder="Product name"
          value={formData.name}
          onChange={(e) => updateField("name", e.target.value)}
          error={errors.name}
        />
        <div className="w-full">
          <label htmlFor="category" className="mb-1.5 block text-sm font-medium text-soft-brown">
            Category
          </label>
          <select
            id="category"
            value={formData.category}
            onChange={(e) => updateField("category", e.target.value)}
            className="h-10 w-full rounded-brand border border-champagne-beige bg-cream px-3 text-soft-brown focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2"
          >
            <option value="">Select category...</option>
            {CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
          {errors.category && (
            <p className="mt-1.5 text-sm text-red-700">{errors.category}</p>
          )}
        </div>
        <Input
          label="Price (EUR)"
          type="number"
          step="0.01"
          min="0"
          placeholder="0.00"
          value={priceDisplay}
          onChange={(e) => setPriceDisplay(e.target.value)}
          onBlur={(e) => {
            const cents = eurToCents(e.target.value);
            updateField("price_cents", cents);
            setPriceDisplay(cents > 0 ? (cents / 100).toFixed(2) : "");
          }}
          error={errors.price_cents}
        />
        <Input
          label="Stock"
          type="number"
          min="0"
          step="1"
          value={String(formData.stock)}
          onChange={(e) => updateField("stock", Math.max(0, Math.floor(Number(e.target.value) || 0)))}
          error={errors.stock}
        />
        <Input
          label="Image URL"
          placeholder="https://..."
          value={formData.image_url}
          onChange={(e) => updateField("image_url", e.target.value)}
        />
        <Input
          label="Materials"
          placeholder="e.g., Soy wax, lavender oil"
          value={formData.materials}
          onChange={(e) => updateField("materials", e.target.value)}
        />
        <Input
          label="Days to Craft"
          type="number"
          min="1"
          placeholder="Optional"
          value={formData.days_to_craft !== null ? String(formData.days_to_craft) : ""}
          onChange={(e) => {
            const val = e.target.value ? parseInt(e.target.value) : null;
            updateField("days_to_craft", val);
          }}
        />
      </div>

      <div>
        <label htmlFor="description" className="mb-1.5 block text-sm font-medium text-soft-brown">
          Description
        </label>
        <textarea
          id="description"
          value={formData.description}
          onChange={(e) => updateField("description", e.target.value)}
          rows={4}
          className="w-full rounded-brand border border-champagne-beige bg-cream px-3 py-2 text-soft-brown placeholder:text-soft-brown/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2"
          placeholder="Describe this product..."
        />
      </div>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="is_featured"
          checked={formData.is_featured}
          onChange={(e) => updateField("is_featured", e.target.checked)}
          className="h-4 w-4 rounded border-champagne-beige text-muted-gold focus:ring-muted-gold"
        />
        <label htmlFor="is_featured" className="text-sm text-soft-brown">
          Featured product (shown on homepage)
        </label>
      </div>

      <div className="flex items-center gap-3 border-t border-champagne-beige pt-6">
        <Button type="submit" isLoading={isSubmitting}>
          {submitLabel}
        </Button>
        <Button
          type="button"
          variant="secondary"
          onClick={() => router.push("/admin/products")}
        >
          Cancel
        </Button>
      </div>
    </form>
  );
}
