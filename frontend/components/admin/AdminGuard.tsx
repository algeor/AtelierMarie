"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAdmin } from "@/contexts/AdminContext";
import enMessages from "@/messages/en.json";
import bgMessages from "@/messages/bg.json";

export function AdminGuard({ children }: { children: React.ReactNode }) {
  const { isAdmin, isLoading } = useAdmin();
  const router = useRouter();
  const params = useParams<{ locale?: string }>();
  const locale = params?.locale === "bg" ? "bg" : "en";
  const loadingMessage = locale === "bg" ? bgMessages.common.loading : enMessages.common.loading;

  useEffect(() => {
    if (!isLoading && !isAdmin) {
      router.replace("/");
    }
  }, [isAdmin, isLoading, router]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-warm-ivory">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-champagne-beige border-t-muted-gold" />
          <p className="text-sm text-soft-brown">{loadingMessage}</p>
        </div>
      </div>
    );
  }

  if (!isAdmin) {
    return null;
  }

  return <>{children}</>;
}
