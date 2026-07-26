import { getProducts, getTaxonomy } from "@/lib/api";
import { ProductListingClient } from "@/components/products/ProductListingClient";
import type { Locale } from "@/i18n/routing";
import { getLocalizedAlternates } from "@/lib/seo";

export async function generateMetadata({ params }: { params: Promise<{ locale: Locale }> }) {
  const { locale } = await params;
  return {
    title: "Our Collection",
    alternates: getLocalizedAlternates(locale, "/products"),
  };
}

export default async function ProductsPage({ params }: { params: Promise<{ locale: Locale }> }) {
  const { locale } = await params;
  const [{ products }, taxonomy] = await Promise.all([
    getProducts(1, 100, locale),
    getTaxonomy(locale),
  ]);

  return <ProductListingClient products={products} taxonomy={taxonomy} />;
}
