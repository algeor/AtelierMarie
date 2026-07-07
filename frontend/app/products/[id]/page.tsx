import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getProduct } from "@/lib/api";
import { ProductImage } from "@/components/products/ProductImage";
import { Badge } from "@/components/ui/Badge";
import { formatPrice } from "@/lib/utils";
import { AddToCartSection } from "@/components/products/AddToCartSection";

interface ProductPageProps {
  params: { id: string };
}

export async function generateMetadata({
  params,
}: ProductPageProps): Promise<Metadata> {
  try {
    const product = await getProduct(params.id);
    return { title: `${product.name} | Atelier Marie` };
  } catch {
    return { title: "Product Not Found | Atelier Marie" };
  }
}

export default async function ProductDetailPage({ params }: ProductPageProps) {
  let product;
  try {
    product = await getProduct(params.id);
  } catch {
    notFound();
  }

  if (!product.is_active) {
    notFound();
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12">
        {/* Product Image */}
        <ProductImage
          name={product.name}
          imageUrl={product.image_url}
          sizes="(max-width: 1024px) 100vw, 50vw"
          priority
        />

        {/* Product Details */}
        <div className="flex flex-col gap-6">
          <div>
            <h1 className="font-heading text-3xl md:text-4xl text-charcoal">
              {product.name}
            </h1>
            <p className="mt-3 text-2xl font-medium text-soft-brown">
              {formatPrice(product.price_cents)}
            </p>
            {product.category && (
              <div className="mt-3">
                <Badge>{product.category}</Badge>
              </div>
            )}
          </div>

          {product.description && (
            <p className="text-soft-brown leading-relaxed">
              {product.description}
            </p>
          )}

          {product.materials && (
            <div>
              <h2 className="font-heading text-lg text-charcoal mb-2">
                Materials & Ingredients
              </h2>
              <p className="text-soft-brown text-sm">{product.materials}</p>
            </div>
          )}

          {product.days_to_craft !== null && (
            <div>
              <h2 className="font-heading text-lg text-charcoal mb-2">
                Crafting Time
              </h2>
              <p className="text-soft-brown text-sm">
                Lovingly handcrafted over {product.days_to_craft} days
              </p>
            </div>
          )}

          {/* Add to Cart section */}
          <AddToCartSection
            productId={product.id}
            stock={product.stock}
          />
        </div>
      </div>
    </div>
  );
}
