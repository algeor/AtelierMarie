import { getProducts } from "@/lib/api";
import { ProductListingClient } from "@/components/products/ProductListingClient";

export const metadata = {
  title: "Our Collection",
};

export default async function ProductsPage() {
  const { products } = await getProducts(1, 100);

  return <ProductListingClient products={products} />;
}
