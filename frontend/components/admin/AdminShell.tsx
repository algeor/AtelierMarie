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
    <div className="admin-shell min-h-screen overflow-x-hidden bg-admin-page text-admin-text">
      <AdminSidebar open={sidebarOpen} onOpenChange={setSidebarOpen} />
      <header
        className={cn(
          "fixed inset-x-0 top-0 z-40 border-b border-admin-border/50 bg-admin-page/95 backdrop-blur transition-[left] duration-200 motion-reduce:transition-none",
          sidebarOpen ? "lg:left-72" : "lg:left-0"
        )}
      >
        <div className="flex h-16 min-w-0 items-center justify-between gap-3 pl-16 pr-3 sm:pl-20 sm:pr-4">
          <div className="min-w-0 truncate px-1 text-xs font-semibold uppercase tracking-wide text-admin-muted sm:text-sm">
            {tAdmin("menuLabel")}
          </div>
          <div className="flex min-w-0 shrink-0 items-center gap-2 sm:gap-4">
            <div className="hidden truncate font-heading text-2xl italic text-admin-text md:block">
              {tCommon("appName")}
            </div>
            <Link
              href="/"
              className="group inline-flex h-11 items-center gap-2 rounded-brand border border-admin-border/60 bg-admin-surface px-2 text-sm font-semibold text-admin-text shadow-sm transition-colors hover:border-admin-accent hover:bg-admin-surface-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-admin-focus focus-visible:ring-offset-2 focus-visible:ring-offset-admin-page motion-reduce:transition-none sm:px-3"
              aria-label={tAdmin("backToStore")}
            >
              <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-admin-accent/15 text-admin-primary transition-colors group-hover:bg-admin-accent/25 motion-reduce:transition-none">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.7} stroke="currentColor" className="h-4 w-4">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
                </svg>
              </span>
              <span className="hidden truncate sm:inline">{tAdmin("backToStore")}</span>
            </Link>
          </div>
        </div>
      </header>
      <main
        className={cn(
          "admin-workspace min-h-screen min-w-0 flex-1 overflow-x-hidden pt-20 transition-[padding-left] duration-200 motion-reduce:transition-none",
          sidebarOpen ? "lg:pl-72" : "lg:pl-0"
        )}
      >
        <div className="min-w-0 max-w-full px-3 pb-8 pt-3 sm:px-6 lg:p-8">
          <AdminPageGuide />
          {children}
        </div>
      </main>
    </div>
  );
}
