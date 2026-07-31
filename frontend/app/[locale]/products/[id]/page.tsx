import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { getProduct } from "@/lib/api";
import { ProductGallery } from "@/components/products/ProductGallery";
import { PriceDisplay } from "@/components/products/PriceDisplay";
import { Badge } from "@/components/ui/Badge";
import { AddToCartSection } from "@/components/products/AddToCartSection";
import { ProductSocialSection } from "@/components/products/ProductSocialSection";
import { ProductViewTracker } from "@/components/products/ProductViewTracker";
import type { Locale } from "@/i18n/routing";
import { LEGAL_IDENTITY } from "@/lib/legal";
import { getLocalizedAlternates } from "@/lib/seo";

interface ProductPageProps {
  params: Promise<{ id: string; locale: Locale }>;
}

export async function generateMetadata({
  params,
}: ProductPageProps): Promise<Metadata> {
  const { id, locale } = await params;
  try {
    const product = await getProduct(id, locale);
    return {
      title: product.name,
      alternates: getLocalizedAlternates(locale, `/products/${id}`),
    };
  } catch {
    const t = await getTranslations({ locale, namespace: "products" });
    return {
      title: t("notFound"),
      alternates: getLocalizedAlternates(locale, `/products/${id}`),
    };
  }
}

export default async function ProductDetailPage({ params }: ProductPageProps) {
  const { id, locale } = await params;
  const t = await getTranslations({ locale, namespace: "products" });
  let product;
  try {
    product = await getProduct(id, locale);
  } catch {
    notFound();
  }

  if (!product.is_active) {
    notFound();
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <ProductViewTracker
        productId={product.id}
        category={product.category}
        valueCents={product.effective_price_cents}
      />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12">
        {/* Product Image */}
        <ProductGallery
          name={product.name}
          images={product.images}
          video={product.video}
          primaryImageUrl={product.primary_image_url}
        />

        {/* Product Details */}
        <div className="flex flex-col gap-6">
          <div>
            <h1 className="font-heading text-3xl md:text-4xl text-charcoal">
              {product.name}
            </h1>
            <p className="mt-3 text-2xl font-medium text-soft-brown">
              <PriceDisplay
                product={product}
                className="text-2xl font-medium text-soft-brown"
              />
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {product.product_type_name && <Badge>{product.product_type_name}</Badge>}
              {product.category_name && <Badge>{product.category_name}</Badge>}
              {product.labels.map((label) => (
                <span
                  key={label.slug}
                  className="rounded-pill bg-champagne-beige/60 px-3 py-1 text-sm text-soft-brown"
                >
                  {label.name}
                </span>
              ))}
            </div>
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

          <section className="rounded-brand border border-champagne-beige bg-cream p-4" aria-labelledby="product-safety-heading">
            <h2 id="product-safety-heading" className="font-heading text-lg text-charcoal">
              {t("safetyTitle")}
            </h2>
            <dl className="mt-3 grid gap-3 text-sm text-soft-brown sm:grid-cols-2">
              <div>
                <dt className="font-medium text-charcoal">{t("productIdentifier")}</dt>
                <dd className="break-words">{product.id}</dd>
              </div>
              <div>
                <dt className="font-medium text-charcoal">{t("responsibleParty")}</dt>
                <dd>{LEGAL_IDENTITY.responsiblePartyName}</dd>
              </div>
              <div>
                <dt className="font-medium text-charcoal">{t("responsiblePartyAddress")}</dt>
                <dd className="break-words">{LEGAL_IDENTITY.responsiblePartyAddress}</dd>
              </div>
              <div>
                <dt className="font-medium text-charcoal">{t("responsiblePartyEmail")}</dt>
                <dd className="break-words">{LEGAL_IDENTITY.responsiblePartyEmail}</dd>
              </div>
            </dl>
            {(product.safety_warnings || product.care_instructions) && (
              <div className="mt-4 space-y-4 text-sm leading-6 text-soft-brown">
                {product.safety_warnings && (
                  <div>
                    <h3 className="font-medium text-charcoal">{t("safetyWarnings")}</h3>
                    <p className="mt-1 whitespace-pre-line">{product.safety_warnings}</p>
                  </div>
                )}
                {product.care_instructions && (
                  <div>
                    <h3 className="font-medium text-charcoal">{t("careInstructions")}</h3>
                    <p className="mt-1 whitespace-pre-line">{product.care_instructions}</p>
                  </div>
                )}
              </div>
            )}
          </section>

          <div className="rounded-brand border border-champagne-beige bg-cream p-4">
            <h2 className="text-sm font-medium text-charcoal">{t("faqLinksTitle")}</h2>
            <div className="mt-3 flex flex-wrap gap-2 text-sm">
              <Link
                href="/faq#care"
                className="rounded-pill bg-white px-3 py-2 text-soft-brown transition-colors duration-fast hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-muted-gold"
              >
                {t("faqCare")}
              </Link>
              <Link
                href="/faq#custom"
                className="rounded-pill bg-white px-3 py-2 text-soft-brown transition-colors duration-fast hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-muted-gold"
              >
                {t("faqCustom")}
              </Link>
              <Link
                href="/faq#shipping"
                className="rounded-pill bg-white px-3 py-2 text-soft-brown transition-colors duration-fast hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-muted-gold"
              >
                {t("faqShipping")}
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Social proof — reactions & comments */}
      <div className="mt-12 pt-8 border-t border-warm-gray/20">
        <ProductSocialSection productId={product.id} />
      </div>
    </div>
  );
}
