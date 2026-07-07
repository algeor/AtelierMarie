"use client";

import { Button } from "@/components/ui/Button";

export default function ProductsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
      <h1 className="font-heading text-3xl text-charcoal mb-4">
        Something went wrong
      </h1>
      <p className="text-soft-brown text-lg mb-8">
        Unable to load products. Please try again later.
      </p>
      <Button onClick={reset} variant="primary">
        Try again
      </Button>
    </div>
  );
}
