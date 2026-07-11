import { getProducts } from "@/lib/api";
import { getTranslations } from "next-intl/server";
import { HeroSection } from "@/components/products/HeroSection";
import { ProductGrid } from "@/components/products/ProductGrid";
import { ProductCard } from "@/components/products/ProductCard";
import type { Locale } from "@/i18n/routing";
import { getLocalizedAlternates } from "@/lib/seo";

export function generateMetadata({ params }: { params: { locale: Locale } }) {
  return {
    title: "Atelier Marie | Luxury Handcrafted Candles",
    alternates: getLocalizedAlternates(params.locale, ""),
  };
}

export default async function HomePage({ params }: { params: { locale: Locale } }) {
  const t = await getTranslations({ locale: params.locale, namespace: "home" });
  const { products } = await getProducts(1, 100, params.locale);
  const featured = products.filter((p) => p.is_featured);

  return (
    <>
      <HeroSection />
      {featured.length > 0 && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <h2 className="font-heading text-3xl text-charcoal mb-8">
            {t("featured")}
          </h2>
          <ProductGrid>
            {featured.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </ProductGrid>
        </div>
      )}
    </>
  );
}
