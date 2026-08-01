"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { AdminPageGuide } from "@/components/admin/AdminPageGuide";
import { AdminSidebar } from "@/components/admin/AdminSidebar";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

export function AdminShell({ children }: { children: React.ReactNode }) {
  const tAdmin = useTranslations("admin");
  const tCommon = useTranslations("common");
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="min-h-screen bg-warm-ivory">
      <AdminSidebar open={sidebarOpen} onOpenChange={setSidebarOpen} />
      <div className="fixed left-16 top-4 z-50 inline-flex h-11 items-center px-2 text-sm font-semibold uppercase tracking-wide text-soft-brown sm:left-20">
        {tAdmin("menuLabel")}
      </div>
      <div className="fixed right-4 top-4 z-50 flex h-11 items-center gap-4">
        <div className="hidden font-heading text-2xl italic text-charcoal sm:block">
          {tCommon("appName")}
        </div>
        <Link
          href="/"
          className="group inline-flex h-11 items-center gap-2 rounded-brand border border-champagne-beige bg-cream px-3 text-sm font-semibold text-charcoal shadow-sm transition-colors hover:border-muted-gold/50 hover:bg-muted-gold/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
        >
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-muted-gold/15 text-muted-gold transition-colors group-hover:bg-muted-gold/25">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.7} stroke="currentColor" className="h-4 w-4">
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
            </svg>
          </span>
          <span>{tAdmin("backToStore")}</span>
        </Link>
      </div>
      <main
        className={cn(
          "min-h-screen flex-1 pt-20 transition-[padding-left] duration-200",
          sidebarOpen ? "lg:pl-72" : "lg:pl-0"
        )}
      >
        <div className="p-6 lg:p-8">
          <AdminPageGuide />
          {children}
        </div>
      </main>
    </div>
  );
}
