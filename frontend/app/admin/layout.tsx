import { AdminProvider } from "@/contexts/AdminContext";
import { AdminGuard } from "@/components/admin/AdminGuard";
import { AdminSidebar } from "@/components/admin/AdminSidebar";

export const metadata = {
  title: "Admin | Atelier Marie",
};

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
