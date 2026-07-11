import { getProducts } from "@/lib/api";
import { ProductListingClient } from "@/components/products/ProductListingClient";
import type { Locale } from "@/i18n/routing";

export const metadata = {
  title: "Our Collection",
};

export default async function ProductsPage({ params }: { params: { locale: Locale } }) {
  const { products } = await getProducts(1, 100, params.locale);

  return <ProductListingClient products={products} />;
}
