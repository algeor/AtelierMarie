import { Link } from "@/i18n/navigation";
import { ProductImage } from "./ProductImage";
import { PriceDisplay } from "./PriceDisplay";
import { AddToCartButton } from "@/components/cart/AddToCartButton";
import type { ProductResponse } from "@/lib/types";

interface ProductCardProps {
  product: ProductResponse;
}

export function ProductCard({ product }: ProductCardProps) {
  return (
    <div className="group">
      <Link
        href={`/products/${product.id}`}
        className="block rounded-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
      >
        <div className="motion-safe:transition-transform motion-safe:duration-300 motion-safe:ease-brand motion-safe:group-hover:-translate-y-1 motion-safe:group-focus-within:-translate-y-1">
          <ProductImage
            name={product.name}
            imageUrl={product.video?.poster_url ?? product.primary_image_url}
            sizes="(max-width: 768px) 100vw, (max-width: 1024px) 50vw, 25vw"
            className="editorial-image-settle shadow-sm shadow-border/10"
          />
          <div className="mt-3 space-y-1">
            <h3 className="font-heading text-base text-charcoal line-clamp-2 leading-snug">
              {product.name}
            </h3>
            <p className="text-sm font-medium text-soft-brown">
              <PriceDisplay product={product} />
            </p>
          </div>
        </div>
      </Link>
      <div className="mt-3">
        <AddToCartButton
          productId={product.id}
          stock={product.stock}
          className="w-full text-sm"
        />
      </div>
    </div>
  );
}
