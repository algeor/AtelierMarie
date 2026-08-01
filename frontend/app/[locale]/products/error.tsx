"use client";

import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/Button";

export default function ProductsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations("products");

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
      <h1 className="font-heading text-3xl text-charcoal mb-4">
        {t("loadErrorTitle")}
      </h1>
      <p className="text-soft-brown text-lg mb-8">
        {t("loadErrorDescription")}
      </p>
      <Button onClick={reset} variant="primary">
        {t("tryAgain")}
      </Button>
    </div>
  );
}
