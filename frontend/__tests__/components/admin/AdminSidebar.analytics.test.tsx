import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AdminSidebar } from "@/components/admin/AdminSidebar";
import { renderWithIntl } from "../../test-utils";

vi.mock("@/contexts/AdminContext", () => ({
  useAdmin: () => ({ user: { name: "Admin", email: "admin@example.com" } }),
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, className, ...props }: { children: React.ReactNode; href: string; className?: string }) => (
    <a href={href} className={className} {...props}>{children}</a>
  ),
  usePathname: () => "/admin/analytics",
}));

describe("AdminSidebar analytics nav", () => {
  it("renders Analytics link with active state", () => {
    renderWithIntl(<AdminSidebar />);

    const link = screen.getByRole("link", { name: /analytics/i });
    expect(link).toHaveAttribute("href", "/admin/analytics");
    expect(link).toHaveAttribute("aria-current", "page");
  });
});
