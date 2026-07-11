"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAdmin } from "@/contexts/AdminContext";
import enMessages from "@/messages/en.json";
import bgMessages from "@/messages/bg.json";

function getLoadingMessage(): string {
  if (typeof window !== "undefined" && window.location.pathname.startsWith("/bg")) {
    return bgMessages.common.loading;
  }
  return enMessages.common.loading;
}

export function AdminGuard({ children }: { children: React.ReactNode }) {
  const { isAdmin, isLoading } = useAdmin();
  const router = useRouter();

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
          <p className="text-sm text-soft-brown">{getLoadingMessage()}</p>
        </div>
      </div>
    );
  }

  if (!isAdmin) {
    return null;
  }

  return <>{children}</>;
}
