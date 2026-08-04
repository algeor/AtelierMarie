"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useAuth } from "@/contexts/AuthContext";
import { UserAvatar } from "@/components/auth/UserAvatar";
import { Skeleton } from "@/components/ui/Skeleton";

export default function AccountPage() {
  const t = useTranslations("auth");
  const { user, isLoading, isAuthenticated, login } = useAuth();

  if (isLoading) {
    return (
      <main className="bg-page px-4 py-12 text-text">
        <div className="mx-auto max-w-2xl">
        <Skeleton className="mb-8 h-8 w-48" />
        <div className="rounded-brand border border-border/60 bg-surface-elevated/75 p-8 shadow-sm">
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
        <div className="rounded-brand border border-border/60 bg-surface-elevated/75 p-8 text-center shadow-sm">
          <h1 className="mb-4 font-heading text-2xl text-text">
            {t("myAccount")}
          </h1>
          <p className="mb-6 text-muted">
            {t("signInToViewAccount")}
          </p>
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
      <div className="mx-auto max-w-2xl">
      <h1 className="mb-8 font-heading text-4xl leading-tight text-text">{t("myAccount")}</h1>
      <div className="rounded-brand border border-border/60 bg-surface-elevated/75 p-8 shadow-sm">
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
      </div>
    </main>
  );
}
