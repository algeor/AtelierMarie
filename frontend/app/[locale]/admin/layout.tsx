import { AdminProvider } from "@/contexts/AdminContext";
import { AdminGuard } from "@/components/admin/AdminGuard";
import { AdminSidebar } from "@/components/admin/AdminSidebar";
import type { Locale } from "@/i18n/routing";
import { getLocalizedAlternates } from "@/lib/seo";

export function generateMetadata({ params }: { params: { locale: Locale } }) {
  return {
    title: "Admin | Atelier Marie",
    alternates: getLocalizedAlternates(params.locale, "/admin"),
  };
}

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AdminProvider>
      <AdminGuard>
        <div className="flex min-h-screen bg-warm-ivory">
          <AdminSidebar />
          <main className="flex-1 pt-16 lg:pl-64 lg:pt-0">
            <div className="p-6 lg:p-8">
              {children}
            </div>
          </main>
        </div>
      </AdminGuard>
    </AdminProvider>
  );
}
