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
  // Products drive the primary "sell candles" page; taxonomy only builds the
  // filter menu. Fetch them independently so a taxonomy endpoint failure
  // degrades the menu (empty facets) instead of taking down the product grid.
  const [{ products }, taxonomy] = await Promise.all([
    getProducts(1, 100, locale),
    getTaxonomy(locale).catch(() => ({
      product_types: [],
      categories: [],
      labels: [],
    })),
  ]);

  return (
    <main>
      <ProductListingClient products={products} taxonomy={taxonomy} />
    </main>
  );
}
