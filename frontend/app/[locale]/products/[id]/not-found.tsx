import Link from "next/link";
import { Button } from "@/components/ui/Button";

export default function ProductNotFound() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
      <h1 className="font-heading text-3xl text-charcoal mb-4">
        Product not found
      </h1>
      <p className="text-soft-brown text-lg mb-8">
        Sorry, we couldn&apos;t find the product you&apos;re looking for. It may have been
        removed or is no longer available.
      </p>
      <Link href="/products">
        <Button variant="primary">Browse Our Collection</Button>
      </Link>
    </div>
  );
}
