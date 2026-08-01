"use client";

import { usePathname } from "@/i18n/navigation";
import { CartDrawer } from "@/components/cart/CartDrawer";
import { AnnouncementBar } from "@/components/layout/AnnouncementBar";
import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";
import { CartProvider } from "@/contexts/CartContext";

function isAdminPath(pathname: string): boolean {
  return pathname === "/admin" || pathname.startsWith("/admin/");
}

export function LocaleChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  if (isAdminPath(pathname)) {
    return <>{children}</>;
  }

  return (
    <CartProvider>
      <AnnouncementBar />
      <Header />
      <CartDrawer />
      <main>{children}</main>
      <Footer />
    </CartProvider>
  );
}
