import { getProducts, getTaxonomy } from "@/lib/api";
import { ProductListingClient } from "@/components/products/ProductListingClient";
import type { Locale } from "@/i18n/routing";
import { getLocalizedAlternates } from "@/lib/seo";

export function generateMetadata({ params }: { params: { locale: Locale } }) {
  return {
    title: "Our Collection",
    alternates: getLocalizedAlternates(params.locale, "/products"),
  };
}

export default async function ProductsPage({ params }: { params: { locale: Locale } }) {
  const [{ products }, taxonomy] = await Promise.all([
    getProducts(1, 100, params.locale),
    getTaxonomy(params.locale),
  ]);

  return <ProductListingClient products={products} taxonomy={taxonomy} />;
}
