import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AdminSidebar } from "@/components/admin/AdminSidebar";
import { renderWithIntl } from "../../test-utils";

let mockedPathname = "/admin/analytics";

vi.mock("@/contexts/AdminContext", () => ({
  useAdmin: () => ({ user: { name: "Admin", email: "admin@example.com" } }),
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, className, ...props }: { children: React.ReactNode; href: string; className?: string }) => (
    <a href={href} className={className} {...props}>{children}</a>
  ),
  usePathname: () => mockedPathname,
}));

describe("AdminSidebar nav", () => {
  beforeEach(() => {
    mockedPathname = "/admin/analytics";
  });

  it("renders Analytics link with active state", () => {
    renderWithIntl(<AdminSidebar />);

    const link = screen.getByRole("link", { name: /analytics/i });
    expect(link).toHaveAttribute("href", "/admin/analytics");
    expect(link).toHaveAttribute("aria-current", "page");
  });

  it("groups Econt and Speedy under Delivery", () => {
    mockedPathname = "/admin/delivery/econt";

    renderWithIntl(<AdminSidebar />);

    const delivery = screen.getByRole("link", { name: "Delivery" });
    const econt = screen.getByRole("link", { name: "Econt" });
    const speedy = screen.getByRole("link", { name: "Speedy" });

    expect(delivery).toHaveAttribute("href", "/admin/delivery");
    expect(econt).toHaveAttribute("href", "/admin/delivery/econt");
    expect(speedy).toHaveAttribute("href", "/admin/delivery/speedy");
    expect(econt).toHaveAttribute("aria-current", "page");
  });
});
