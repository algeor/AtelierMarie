import { getProducts } from "@/lib/api";
import { HeroSection } from "@/components/products/HeroSection";
import { ProductGrid } from "@/components/products/ProductGrid";
import { ProductCard } from "@/components/products/ProductCard";

export const metadata = {
  title: "Atelier Marie | Luxury Handcrafted Candles",
};

export default async function HomePage() {
  const { products } = await getProducts(1, 100);
  const featured = products.filter((p) => p.is_featured);

  return (
    <>
      <HeroSection />
      {featured.length > 0 && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <h2 className="font-heading text-3xl text-charcoal mb-8">Featured</h2>
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
