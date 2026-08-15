"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { useAdmin } from "@/contexts/AdminContext";
import { getAdminAbout, getAdminCookies, getAdminFaq, getAdminPrivacy, getAdminTerms } from "@/lib/api";
import { cn } from "@/lib/utils";

interface NavChild {
  label?: string;
  labelKey?: string;
  href: string;
  activeHrefs?: string[];
}

interface NavItem {
  labelKey: string;
  href: string;
  icon?: ReactNode;
  activeHrefs?: string[];
  children?: NavChild[];
}

interface NavGroup {
  key: string;
  labelKey: string;
  icon: ReactNode;
  activeHrefs?: string[];
  items: NavItem[];
}

function GridIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
    </svg>
  );
}

function ProductIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
    </svg>
  );
}

function InventoryIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5v8.25a2.25 2.25 0 01-1.244 2.013l-6 3a2.25 2.25 0 01-2.012 0l-6-3A2.25 2.25 0 013.75 15.75V7.5m16.5 0L12 3.375 3.75 7.5m16.5 0L12 11.625 3.75 7.5M12 21V11.625" />
    </svg>
  );
}

function OrdersIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z" />
    </svg>
  );
}

function AccountingIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 7.5h6m-6 3h6m-6 3h3M6.75 3.75h10.5A2.25 2.25 0 0119.5 6v12A2.25 2.25 0 0117.25 20.25H6.75A2.25 2.25 0 014.5 18V6A2.25 2.25 0 016.75 3.75z" />
    </svg>
  );
}

function AnalyticsIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.5h4.5v6H3v-6zm6.75-9h4.5v15h-4.5v-15zm6.75 5.25H21v9.75h-4.5V9.75z" />
    </svg>
  );
}

function DeliveryIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 18.75a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zm10.5 0a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 6.75h11.25v8.25H3V6.75zm11.25 3h3.57c.4 0 .78.19 1.02.51l2.16 2.88v1.86h-6.75V9.75zM5.25 18.75H3.75a.75.75 0 01-.75-.75v-3h18v3a.75.75 0 01-.75.75h-1.5m-10.5 0h7.5" />
    </svg>
  );
}

function PaymentIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 8.25h19.5m-18 3.75h16.5m-14.25 4.5h3.75m3 0h4.5M4.5 6h15a1.5 1.5 0 011.5 1.5v9A1.5 1.5 0 0119.5 18h-15A1.5 1.5 0 013 16.5v-9A1.5 1.5 0 014.5 6z" />
    </svg>
  );
}

function TagIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.568 3H5.25A2.25 2.25 0 003 5.25v4.318c0 .597.237 1.17.659 1.591l9.581 9.581c.699.699 1.78.872 2.607.33a18.095 18.095 0 005.223-5.223c.542-.827.369-1.908-.33-2.607L11.16 3.66A2.25 2.25 0 009.568 3z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 6h.008v.008H6V6z" />
    </svg>
  );
}

function PagesIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.75c-2.7-1.8-5.25-1.8-7.5-.45v11.4c2.25-1.35 4.8-1.35 7.5.45m0-11.4c2.7-1.8 5.25-1.8 7.5-.45v11.4c-2.25-1.35-4.8-1.35-7.5.45m0-11.4v11.4" />
    </svg>
  );
}

function HelpIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.178-.43.326-.67.442-.745.361-1.451.999-1.451 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z" />
    </svg>
  );
}

function ChevronIcon({ expanded }: { expanded: boolean }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      className={cn("h-4 w-4 transition-transform motion-reduce:transition-none", expanded && "rotate-180")}
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
    </svg>
  );
}

const NAV_GROUPS: NavGroup[] = [
  {
    key: "work",
    labelKey: "workNav",
    icon: <GridIcon />,
    items: [
      { labelKey: "dashboard", href: "/admin", icon: <GridIcon /> },
      { labelKey: "orders", href: "/admin/orders", icon: <OrdersIcon /> },
      { labelKey: "analytics.navLabel", href: "/admin/analytics", icon: <AnalyticsIcon /> },
      {
        labelKey: "deliveryNav",
        href: "/admin/delivery",
        icon: <DeliveryIcon />,
        activeHrefs: ["/admin/econt", "/admin/speedy"],
        children: [
          { labelKey: "econtNav", href: "/admin/delivery/econt", activeHrefs: ["/admin/econt"] },
          { labelKey: "speedyNav", href: "/admin/delivery/speedy", activeHrefs: ["/admin/speedy"] },
        ],
      },
    ],
  },
  {
    key: "catalog",
    labelKey: "catalogNav",
    icon: <ProductIcon />,
    items: [
      { labelKey: "products", href: "/admin/products", icon: <ProductIcon /> },
      { labelKey: "taxonomy.navLabel", href: "/admin/taxonomy", icon: <TagIcon /> },
      { labelKey: "promotionsNav", href: "/admin/promotions", icon: <TagIcon /> },
    ],
  },
  {
    key: "inventoryProduction",
    labelKey: "inventoryProductionNav",
    icon: <InventoryIcon />,
    activeHrefs: ["/admin/inventory"],
    items: [
      { labelKey: "materialsNav", href: "/admin/inventory/materials" },
      { labelKey: "recipesNav", href: "/admin/inventory/recipes" },
      { labelKey: "productionBatchesNav", href: "/admin/inventory/batches" },
      { labelKey: "valuationNav", href: "/admin/inventory/valuation" },
    ],
  },
  {
    key: "finance",
    labelKey: "financeNav",
    icon: <AccountingIcon />,
    items: [
      { labelKey: "accountingNav", href: "/admin/accounting", icon: <AccountingIcon /> },
      { labelKey: "paymentSettingsNav", href: "/admin/settings/payments", icon: <PaymentIcon /> },
    ],
  },
  {
    key: "pages",
    labelKey: "pagesNav",
    icon: <PagesIcon />,
    items: [
      { labelKey: "siteMediaNav", href: "/admin/site-media", icon: <PagesIcon /> },
      { labelKey: "homeNav", href: "/admin/home", icon: <PagesIcon /> },
      { labelKey: "atelierNav", href: "/admin/atelier", icon: <PagesIcon /> },
      { labelKey: "termsNav", href: "/admin/terms", icon: <PagesIcon /> },
      { labelKey: "privacyNav", href: "/admin/privacy", icon: <PagesIcon /> },
      { labelKey: "cookiesNav", href: "/admin/cookies", icon: <PagesIcon /> },
      { labelKey: "legalNav", href: "/admin/legal", icon: <PagesIcon /> },
      { labelKey: "faqNav", href: "/admin/faq", icon: <HelpIcon /> },
    ],
  },
];

const DEFAULT_EXPANDED_GROUPS = {
  work: true,
  catalog: true,
  inventoryProduction: false,
  finance: false,
  pages: true,
};

interface AdminSidebarProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function AdminSidebar({ open, onOpenChange }: AdminSidebarProps = {}) {
  const t = useTranslations("admin");
  const pathname = usePathname();
  const { user } = useAdmin();
  const [internalOpen, setInternalOpen] = useState(true);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>(DEFAULT_EXPANDED_GROUPS);
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>({});
  const [dynamicChildren, setDynamicChildren] = useState<Record<string, NavChild[]>>({});
  const sidebarOpen = open ?? internalOpen;
  const setSidebarOpen = onOpenChange ?? setInternalOpen;

  useEffect(() => {
    let cancelled = false;

    async function loadPageParts() {
      const [about, faq, terms, privacy, cookies] = await Promise.allSettled([
        getAdminAbout(),
        getAdminFaq(),
        getAdminTerms(),
        getAdminPrivacy(),
        getAdminCookies(),
      ]);

      if (cancelled) return;

      setDynamicChildren({
        "/admin/atelier": about.status === "fulfilled"
          ? about.value.sections.map((section, index) => ({
              label: `${String(index + 1).padStart(2, "0")} · ${section.heading_en || section.slug}`,
              href: `/admin/atelier?section=${encodeURIComponent(section.slug)}&part=content`,
            }))
          : [],
        "/admin/faq": faq.status === "fulfilled"
          ? faq.value.sections.map((section) => ({
              label: section.title_en,
              href: `/admin/faq?section=${encodeURIComponent(section.slug)}&part=questions`,
            }))
          : [],
        "/admin/terms": terms.status === "fulfilled"
          ? [
              { label: "Page fields", href: "/admin/terms?target=page" },
              ...terms.value.sections.map((section) => ({
                label: `${section.title_en} (${section.body_en.length} paragraph${section.body_en.length === 1 ? "" : "s"})`,
                href: `/admin/terms?target=${encodeURIComponent(section.slug)}`,
              })),
            ]
          : [],
        "/admin/privacy": privacy.status === "fulfilled"
          ? [
              { label: "Page fields", href: "/admin/privacy?target=page" },
              ...privacy.value.sections.map((section) => ({
                label: `${section.title_en} (${section.body_en.length} paragraph${section.body_en.length === 1 ? "" : "s"})`,
                href: `/admin/privacy?target=${encodeURIComponent(section.slug)}`,
              })),
            ]
          : [],
        "/admin/cookies": cookies.status === "fulfilled"
          ? [
              { label: "Page fields", href: "/admin/cookies?target=page" },
              { label: `Inventory (${cookies.value.cookies.length} row${cookies.value.cookies.length === 1 ? "" : "s"})`, href: "/admin/cookies?target=inventory" },
              ...cookies.value.sections.map((section) => ({
                label: `${section.title_en} (${section.body_en.length} paragraph${section.body_en.length === 1 ? "" : "s"})`,
                href: `/admin/cookies?target=section:${encodeURIComponent(section.slug)}`,
              })),
            ]
          : [],
      });
    }

    void loadPageParts();

    return () => {
      cancelled = true;
    };
  }, []);

  function closeOnMobile() {
    if (typeof window === "undefined" || window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
  }

  function isActive(href: string, activeHrefs: string[] = []): boolean {
    const candidates = [href, ...activeHrefs];
    return candidates.some((candidate) => {
      if (candidate === "/admin") return pathname === "/admin";
      return pathname === candidate || pathname.startsWith(`${candidate}/`);
    });
  }

  function isCurrentLink(href: string, activeHrefs: string[] = []): boolean {
    return pathname === href || activeHrefs.includes(pathname);
  }

  function getItemChildren(item: NavItem): NavChild[] {
    return dynamicChildren[item.href] ?? item.children ?? [];
  }

  function getChildLabel(child: NavChild): string {
    return child.label ?? (child.labelKey ? t(child.labelKey) : child.href);
  }

  function isItemActive(item: NavItem): boolean {
    return isActive(item.href, item.activeHrefs) || getItemChildren(item).some((child) => isActive(child.href, child.activeHrefs));
  }

  function isGroupActive(group: NavGroup): boolean {
    return (group.activeHrefs?.some((href) => isActive(href)) ?? false) || group.items.some(isItemActive);
  }

  function toggleGroup(groupKey: string) {
    setExpandedGroups((current) => ({ ...current, [groupKey]: !current[groupKey] }));
  }

  function toggleItem(itemKey: string) {
    setExpandedItems((current) => ({ ...current, [itemKey]: !current[itemKey] }));
  }

  function renderItem(item: NavItem) {
    const itemActive = isItemActive(item);
    const itemChildren = getItemChildren(item);
    const itemExpanded = Boolean(expandedItems[item.href] || itemActive);
    const linkClassName = cn(
      "flex min-h-10 w-full min-w-0 items-center gap-2 rounded-brand px-3 py-2.5 text-left text-sm font-medium transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-admin-focus focus-visible:ring-offset-2 focus-visible:ring-offset-admin-surface motion-reduce:transition-none",
      itemActive ? "bg-admin-accent/15 text-admin-text" : "text-admin-muted hover:bg-admin-surface-muted/50 hover:text-admin-text"
    );

    if (itemChildren.length === 0) {
      return (
        <Link
          key={item.href}
          href={item.href}
          onClick={closeOnMobile}
          className={linkClassName}
          aria-current={isCurrentLink(item.href, item.activeHrefs) ? "page" : undefined}
        >
          <span className="min-w-0 truncate">{t(item.labelKey)}</span>
        </Link>
      );
    }

    const itemLabel = t(item.labelKey);

    return (
      <div key={item.href}>
        <div className={cn(linkClassName, "pr-1")}>
          <Link
            href={item.href}
            onClick={closeOnMobile}
            className="min-w-0 flex-1 truncate focus-visible:outline-none"
            aria-current={isCurrentLink(item.href, item.activeHrefs) ? "page" : undefined}
          >
            {itemLabel}
          </Link>
          <button
            type="button"
            onClick={() => toggleItem(item.href)}
            className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-brand text-admin-muted transition-colors hover:bg-admin-surface hover:text-admin-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-admin-focus focus-visible:ring-offset-2 focus-visible:ring-offset-admin-surface motion-reduce:transition-none"
            aria-label={t(itemExpanded ? "collapseNavGroup" : "expandNavGroup", { group: itemLabel })}
            aria-expanded={itemExpanded}
          >
            <ChevronIcon expanded={itemExpanded} />
          </button>
        </div>
        {itemExpanded && (
          <div className="ml-4 mt-1 space-y-1 border-l border-admin-border/50 pl-3">
            {itemChildren.map((child) => {
              const childActive = isActive(child.href, child.activeHrefs);
              const childLabel = getChildLabel(child);
              return (
                <Link
                  key={child.href}
                  href={child.href}
                  onClick={closeOnMobile}
                  className={cn(
                    "flex min-h-9 min-w-0 items-center rounded-brand px-3 py-2 text-sm font-medium transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-admin-focus focus-visible:ring-offset-2 focus-visible:ring-offset-admin-surface motion-reduce:transition-none",
                    childActive ? "bg-admin-accent/15 text-admin-text" : "text-admin-muted hover:bg-admin-surface-muted/50 hover:text-admin-text"
                  )}
                  aria-current={childActive ? "page" : undefined}
                >
                  <span className="min-w-0 truncate">{childLabel}</span>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setSidebarOpen(true)}
        className={cn(
          "fixed left-4 top-4 z-50 inline-flex h-11 w-11 items-center justify-center rounded-brand border border-admin-border/60 bg-admin-surface text-admin-muted shadow-sm transition-colors hover:bg-admin-surface-muted/50 hover:text-admin-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-admin-focus focus-visible:ring-offset-2 focus-visible:ring-offset-admin-page motion-reduce:transition-none",
          sidebarOpen && "hidden"
        )}
        aria-label={t("openNavMenu")}
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
        </svg>
      </button>

      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-admin-text/35 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-[min(18.5rem,calc(100vw-0.75rem))] max-w-full flex-col border-r border-admin-border/60 bg-admin-surface shadow-xl transition-transform duration-200 motion-reduce:transition-none lg:w-72 lg:shadow-none",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="border-b border-admin-border/50 p-3">
          <div className="mb-3 flex items-center justify-end">
            <button
              type="button"
              onClick={() => setSidebarOpen(false)}
              className="inline-flex h-10 w-10 items-center justify-center rounded-brand text-admin-muted transition-colors hover:bg-admin-surface-muted/50 hover:text-admin-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-admin-focus focus-visible:ring-offset-2 focus-visible:ring-offset-admin-surface motion-reduce:transition-none"
              aria-label={t("closeNavMenu")}
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <nav className="flex-1 space-y-2 overflow-y-auto px-3 py-4">
          {NAV_GROUPS.map((group) => {
            const groupActive = isGroupActive(group);
            const groupExpanded = Boolean(expandedGroups[group.key] || groupActive);
            const groupLabel = t(group.labelKey);

            return (
              <section key={group.key} aria-label={groupLabel}>
                <button
                  type="button"
                  onClick={() => toggleGroup(group.key)}
                  className={cn(
                    "flex w-full min-w-0 items-center gap-3 rounded-brand px-3 py-2 text-xs font-semibold uppercase tracking-wide transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-admin-focus focus-visible:ring-offset-2 focus-visible:ring-offset-admin-surface motion-reduce:transition-none",
                    groupActive ? "bg-admin-accent/20 text-admin-text" : "text-admin-muted hover:bg-admin-surface-muted/50 hover:text-admin-text"
                  )}
                  aria-expanded={groupExpanded}
                  aria-label={t(groupExpanded ? "collapseNavGroup" : "expandNavGroup", { group: groupLabel })}
                >
                  <span className="shrink-0">{group.icon}</span>
                  <span className="min-w-0 flex-1 truncate text-left">{groupLabel}</span>
                  <ChevronIcon expanded={groupExpanded} />
                </button>
                {groupExpanded && (
                  <div className="ml-4 mt-1 space-y-1 border-l border-admin-border/50 pl-3">
                    {group.items.map(renderItem)}
                  </div>
                )}
              </section>
            );
          })}
        </nav>

        <div className="border-t border-admin-border/50 p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-admin-accent/20 text-sm font-medium text-admin-primary">
              {user?.name?.charAt(0) || "A"}
            </div>
            <div className="flex-1 truncate">
              <p className="truncate text-sm font-medium text-admin-text">
                {user?.name || "Admin"}
              </p>
              <p className="truncate text-xs text-admin-muted">
                {user?.email || ""}
              </p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
