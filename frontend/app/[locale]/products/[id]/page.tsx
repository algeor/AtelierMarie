import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { getProduct } from "@/lib/api";
import { ProductImage } from "@/components/products/ProductImage";
import { Badge } from "@/components/ui/Badge";
import { formatPrice } from "@/lib/utils";
import { AddToCartSection } from "@/components/products/AddToCartSection";
import { ProductSocialSection } from "@/components/products/ProductSocialSection";
import type { Locale } from "@/i18n/routing";
import { getLocalizedAlternates } from "@/lib/seo";

interface ProductPageProps {
  params: { id: string; locale: Locale };
}

export async function generateMetadata({
  params,
}: ProductPageProps): Promise<Metadata> {
  try {
    const product = await getProduct(params.id, params.locale);
    return {
      title: product.name,
      alternates: getLocalizedAlternates(params.locale, `/products/${params.id}`),
    };
  } catch {
    const t = await getTranslations({ locale: params.locale, namespace: "products" });
    return {
      title: t("notFound"),
      alternates: getLocalizedAlternates(params.locale, `/products/${params.id}`),
    };
  }
}

export default async function ProductDetailPage({ params }: ProductPageProps) {
  const t = await getTranslations({ locale: params.locale, namespace: "products" });
  let product;
  try {
    product = await getProduct(params.id, params.locale);
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
                {t("materials")}
              </h2>
              <p className="text-soft-brown text-sm">{product.materials}</p>
            </div>
          )}

          {product.days_to_craft !== null && (
            <div>
              <h2 className="font-heading text-lg text-charcoal mb-2">
                {t("craftingTime")}
              </h2>
              <p className="text-soft-brown text-sm">
                {t("craftingTimeDays", { count: product.days_to_craft })}
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

      {/* Social proof — reactions & comments */}
      <div className="mt-12 pt-8 border-t border-warm-gray/20">
        <ProductSocialSection productId={product.id} />
      </div>
    </div>
  );
}
