"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useAuth } from "@/contexts/AuthContext";
import { useSavedProducts } from "@/contexts/SavedProductsContext";
import { UserAvatar } from "@/components/auth/UserAvatar";
import { ProductCard } from "@/components/products/ProductCard";
import { ProductGrid } from "@/components/products/ProductGrid";
import { Skeleton } from "@/components/ui/Skeleton";

export default function AccountPage() {
  const t = useTranslations("auth");
  const { user, isLoading, isAuthenticated, login } = useAuth();
  const {
    savedProducts,
    savedCount,
    isLoading: savedLoading,
  } = useSavedProducts();

  if (isLoading) {
    return (
      <main className="bg-page px-4 py-12 text-text">
        <div className="mx-auto max-w-2xl">
          <Skeleton className="mb-8 h-8 w-48" />
          <div className="editorial-soft-panel rounded-brand p-8">
            <div className="flex flex-col items-center gap-4">
              <Skeleton className="h-24 w-24 rounded-full" />
              <Skeleton className="h-6 w-40" />
              <Skeleton className="h-5 w-56" />
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (!isAuthenticated || !user) {
    return (
      <main className="bg-page px-4 py-12 text-text">
        <div className="mx-auto max-w-2xl">
          <div className="editorial-soft-panel rounded-brand p-8 text-center">
            <h1 className="mb-4 font-heading text-2xl text-text">
              {t("myAccount")}
            </h1>
            <p className="mb-6 text-muted">{t("signInToViewAccount")}</p>
            <button
              onClick={login}
              className="inline-flex items-center justify-center rounded-brand bg-primary px-6 py-3 font-medium text-primary-foreground transition-colors duration-fast hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
            >
              {t("signInWithGoogle")}
            </button>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="bg-page px-4 py-12 text-text">
      <div className="mx-auto max-w-5xl">
        <h1 className="mb-8 font-heading text-4xl leading-tight text-text">
          {t("myAccount")}
        </h1>
        <div className="editorial-soft-panel mx-auto max-w-2xl rounded-brand p-8">
          <div className="flex flex-col items-center gap-4">
            <UserAvatar
              name={user.name}
              email={user.email}
              avatarUrl={user.avatar_url}
              alt={user.name ?? t("userAvatar")}
              size="lg"
            />
            <h2 className="text-xl font-medium text-text">
              {user.name ?? t("userFallback")}
            </h2>
            <p className="text-muted">{user.email}</p>

            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/orders"
                className="inline-flex items-center justify-center rounded-brand bg-primary px-6 py-3 font-medium text-primary-foreground transition-colors duration-fast hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
              >
                {t("myOrders")}
              </Link>
            </div>
          </div>
        </div>

        <section
          id="saved-products"
          className="mt-12 border-t editorial-divider pt-8"
        >
          <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="font-heading text-2xl text-text">
                {t("savedProducts")}
              </h2>
              <p className="mt-1 text-sm text-muted">
                {t("savedProductsCount", { count: savedCount })}
              </p>
            </div>
            <Link
              href="/products"
              className="w-fit rounded-brand text-sm font-medium text-muted underline-offset-4 transition-colors duration-fast hover:text-text hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
            >
              {t("browseProducts")}
            </Link>
          </div>

          {savedLoading ? (
            <ProductGrid className="lg:grid-cols-3">
              {[1, 2, 3].map((item) => (
                <div key={item} className="space-y-3">
                  <Skeleton className="aspect-[4/5] w-full rounded-brand" />
                  <Skeleton className="h-5 w-3/4" />
                  <Skeleton className="h-5 w-24" />
                </div>
              ))}
            </ProductGrid>
          ) : savedProducts.length > 0 ? (
            <ProductGrid className="lg:grid-cols-3">
              {savedProducts.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </ProductGrid>
          ) : (
            <div className="editorial-note-panel rounded-brand p-5">
              <p className="text-sm leading-6 text-muted">
                {t("noSavedProducts")}
              </p>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
