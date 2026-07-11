"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useAuth } from "@/contexts/AuthContext";
import { Skeleton } from "@/components/ui/Skeleton";

export default function AccountPage() {
  const t = useTranslations("auth");
  const { user, isLoading, isAuthenticated, login } = useAuth();

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-12">
        <Skeleton className="h-8 w-48 mb-8" />
        <div className="bg-white rounded-brand p-8 shadow-sm border border-champagne-beige">
          <div className="flex flex-col items-center gap-4">
            <Skeleton className="w-24 h-24 rounded-full" />
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-5 w-56" />
          </div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-12">
        <div className="bg-white rounded-brand p-8 shadow-sm border border-champagne-beige text-center">
          <h1 className="font-heading text-2xl text-charcoal mb-4">
            {t("myAccount")}
          </h1>
          <p className="text-soft-brown mb-6">
            {t("signInToViewAccount")}
          </p>
          <button
            onClick={login}
            className="inline-flex items-center justify-center px-6 py-3 bg-charcoal text-warm-ivory font-medium rounded-brand hover:bg-soft-brown transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2"
          >
            {t("signInWithGoogle")}
          </button>
        </div>
      </div>
    );
  }

  const initial = user.name?.charAt(0).toUpperCase() ?? user.email.charAt(0).toUpperCase();

  return (
    <div className="max-w-2xl mx-auto px-4 py-12">
      <h1 className="font-heading text-3xl text-charcoal mb-8">{t("myAccount")}</h1>
      <div className="bg-white rounded-brand p-8 shadow-sm border border-champagne-beige">
        <div className="flex flex-col items-center gap-4">
          {user.avatar_url ? (
            <img
              src={user.avatar_url}
              alt={user.name ?? t("userAvatar")}
              className="w-24 h-24 rounded-full object-cover"
            />
          ) : (
            <span className="w-24 h-24 rounded-full bg-muted-gold text-charcoal flex items-center justify-center text-3xl font-medium">
              {initial}
            </span>
          )}
          <h2 className="text-xl font-medium text-charcoal">
            {user.name ?? t("userFallback")}
          </h2>
          <p className="text-soft-brown">{user.email}</p>

          <div className="mt-6 flex flex-col sm:flex-row gap-3">
            <Link
              href="/orders"
              className="inline-flex items-center justify-center px-6 py-3 bg-charcoal text-warm-ivory font-medium rounded-brand hover:bg-soft-brown transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2"
            >
              {t("myOrders")}
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
