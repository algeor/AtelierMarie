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
import { loadLegalIdentity } from "@/lib/legal";
import {
  buildProductJsonLd,
  getLocalizedAlternates,
  serializeJsonLd,
} from "@/lib/seo";

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
  const productJsonLd = buildProductJsonLd(product, locale);

  const legalIdentity = await loadLegalIdentity();

  return (
    <main className="editorial-band px-4 py-10 text-text sm:px-6 lg:px-8 lg:py-16">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: serializeJsonLd(productJsonLd) }}
      />
      <ProductViewTracker
        productId={product.id}
        category={product.category}
        valueCents={product.effective_price_cents}
      />
      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-10 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,0.85fr)] lg:gap-14">
        {/* Product Image */}
        <ProductGallery
          name={product.name}
          images={product.images}
          video={product.video}
          primaryImageUrl={product.primary_image_url}
        />

        {/* Product Details */}
        <div className="flex flex-col gap-6 lg:pt-6">
          <div>
            <h1 className="font-heading text-4xl leading-tight text-text md:text-5xl">
              {product.name}
            </h1>
            <p className="mt-4 text-2xl font-medium text-muted">
              <PriceDisplay
                product={product}
                className="text-2xl font-medium text-muted"
              />
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {product.product_type_name && (
                <Badge>{product.product_type_name}</Badge>
              )}
              {product.category_name && <Badge>{product.category_name}</Badge>}
              {product.labels.map((label) => (
                <span
                  key={label.slug}
                  className="rounded-pill bg-secondary px-3 py-1 text-sm text-secondary-foreground"
                >
                  {label.name}
                </span>
              ))}
            </div>
          </div>

          {product.description && (
            <p className="max-w-prose text-base leading-7 text-muted">
              {product.description}
            </p>
          )}

          {product.materials && (
            <div>
              <h2 className="mb-2 font-heading text-lg text-text">
                {t("materials")}
              </h2>
              <p className="text-sm leading-6 text-muted">
                {product.materials}
              </p>
            </div>
          )}

          {product.days_to_craft !== null && (
            <div>
              <h2 className="mb-2 font-heading text-lg text-text">
                {t("craftingTime")}
              </h2>
              <p className="text-sm leading-6 text-muted">
                {t("craftingTimeDays", { count: product.days_to_craft })}
              </p>
            </div>
          )}

          {/* Add to Cart section */}
          <AddToCartSection productId={product.id} stock={product.stock} />

          <section
            className="editorial-paper-panel rounded-brand p-5"
            aria-labelledby="product-safety-heading"
          >
            <h2
              id="product-safety-heading"
              className="font-heading text-lg text-text"
            >
              {t("safetyTitle")}
            </h2>
            <dl className="mt-3 grid gap-3 text-sm text-muted sm:grid-cols-2">
              <div>
                <dt className="font-medium text-text">
                  {t("productIdentifier")}
                </dt>
                <dd className="break-words">{product.id}</dd>
              </div>
              <div>
                <dt className="font-medium text-text">
                  {t("responsibleParty")}
                </dt>
                <dd>{legalIdentity.responsiblePartyName}</dd>
              </div>
              <div>
                <dt className="font-medium text-text">
                  {t("responsiblePartyAddress")}
                </dt>
                <dd className="break-words">
                  {legalIdentity.responsiblePartyAddress}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-text">
                  {t("responsiblePartyEmail")}
                </dt>
                <dd className="break-words">
                  {legalIdentity.responsiblePartyEmail}
                </dd>
              </div>
            </dl>
            {(product.safety_warnings || product.care_instructions) && (
              <div className="mt-4 space-y-4 text-sm leading-6 text-muted">
                {product.safety_warnings && (
                  <div>
                    <h3 className="font-medium text-text">
                      {t("safetyWarnings")}
                    </h3>
                    <p className="mt-1 whitespace-pre-line">
                      {product.safety_warnings}
                    </p>
                  </div>
                )}
                {product.care_instructions && (
                  <div>
                    <h3 className="font-medium text-text">
                      {t("careInstructions")}
                    </h3>
                    <p className="mt-1 whitespace-pre-line">
                      {product.care_instructions}
                    </p>
                  </div>
                )}
              </div>
            )}
          </section>

          <div className="editorial-note-panel rounded-brand p-5">
            <h2 className="text-sm font-medium text-text">
              {t("faqLinksTitle")}
            </h2>
            <div className="mt-3 flex flex-wrap gap-2 text-sm">
              <Link
                href="/faq#care"
                className="rounded-pill bg-surface px-3 py-2 text-muted transition-colors duration-fast hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
              >
                {t("faqCare")}
              </Link>
              <Link
                href="/faq#custom"
                className="rounded-pill bg-surface px-3 py-2 text-muted transition-colors duration-fast hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
              >
                {t("faqCustom")}
              </Link>
              <Link
                href="/faq#shipping"
                className="rounded-pill bg-surface px-3 py-2 text-muted transition-colors duration-fast hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
              >
                {t("faqShipping")}
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Social proof — reactions & comments */}
      <div className="mx-auto mt-14 max-w-7xl border-t editorial-divider pt-8">
        <ProductSocialSection productId={product.id} />
      </div>
    </main>
  );
}
