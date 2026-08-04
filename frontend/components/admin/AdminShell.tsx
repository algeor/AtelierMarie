"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { AdminPageGuide } from "@/components/admin/AdminPageGuide";
import { AdminSidebar } from "@/components/admin/AdminSidebar";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

export function AdminShell({ children }: { children: React.ReactNode }) {
  const tAdmin = useTranslations("admin");
  const tCommon = useTranslations("common");
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const mediaQuery = window.matchMedia("(min-width: 1024px)");

    function syncSidebar(event: MediaQueryListEvent | MediaQueryList) {
      setSidebarOpen(event.matches);
    }

    syncSidebar(mediaQuery);
    mediaQuery.addEventListener("change", syncSidebar);
    return () => mediaQuery.removeEventListener("change", syncSidebar);
  }, []);

  return (
    <div className="admin-shell min-h-screen bg-admin-page text-admin-text">
      <AdminSidebar open={sidebarOpen} onOpenChange={setSidebarOpen} />
      <div className="fixed left-16 top-4 z-50 inline-flex h-11 items-center px-2 text-sm font-semibold uppercase tracking-wide text-admin-muted sm:left-20">
        {tAdmin("menuLabel")}
      </div>
      <div className="fixed right-3 top-4 z-50 flex h-11 items-center gap-2 sm:right-4 sm:gap-4">
        <div className="hidden font-heading text-2xl italic text-admin-text sm:block">
          {tCommon("appName")}
        </div>
        <Link
          href="/"
          className="group inline-flex h-11 items-center gap-2 rounded-brand border border-admin-border/60 bg-admin-surface px-3 text-sm font-semibold text-admin-text shadow-sm transition-colors hover:border-admin-accent hover:bg-admin-surface-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-admin-focus focus-visible:ring-offset-2 focus-visible:ring-offset-admin-page motion-reduce:transition-none"
        >
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-admin-accent/15 text-admin-primary transition-colors group-hover:bg-admin-accent/25 motion-reduce:transition-none">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.7} stroke="currentColor" className="h-4 w-4">
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
            </svg>
          </span>
          <span>{tAdmin("backToStore")}</span>
        </Link>
      </div>
      <main
        className={cn(
          "admin-workspace min-h-screen flex-1 pt-20 transition-[padding-left] duration-200 motion-reduce:transition-none",
          sidebarOpen ? "lg:pl-72" : "lg:pl-0"
        )}
      >
        <div className="px-4 pb-8 pt-3 sm:px-6 lg:p-8">
          <AdminPageGuide />
          {children}
        </div>
      </main>
    </div>
  );
}
