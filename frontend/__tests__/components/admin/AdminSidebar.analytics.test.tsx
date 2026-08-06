import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AdminShell } from "@/components/admin/AdminShell";
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

vi.mock("@/lib/api", () => ({
  getAdminAbout: vi.fn(async () => ({
    sections: [{ slug: "hero", heading_en: "Atelier hero" }],
  })),
  getAdminFaq: vi.fn(async () => ({
    sections: [{ slug: "care", title_en: "Candle care" }],
  })),
  getAdminTerms: vi.fn(async () => ({
    sections: [{ slug: "returns", title_en: "Returns", body_en: ["One"] }],
  })),
  getAdminPrivacy: vi.fn(async () => ({
    sections: [{ slug: "controller", title_en: "Controller", body_en: ["One", "Two"] }],
  })),
  getAdminCookies: vi.fn(async () => ({
    cookies: [{ name: "atelier_cookie_consent" }],
    sections: [{ slug: "controls", title_en: "Cookie controls", body_en: ["One"] }],
  })),
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

    const delivery = screen.getByRole("button", { name: /collapse delivery/i });
    const econt = screen.getByRole("link", { name: "Econt" });
    const speedy = screen.getByRole("link", { name: "Speedy" });

    expect(delivery).toHaveAttribute("aria-expanded", "true");
    expect(econt).toHaveAttribute("href", "/admin/delivery/econt");
    expect(speedy).toHaveAttribute("href", "/admin/delivery/speedy");
    expect(econt).toHaveAttribute("aria-current", "page");
  });

  it("groups editable pages", async () => {
    const user = userEvent.setup();
    renderWithIntl(<AdminSidebar />);

    expect(screen.getByRole("button", { name: /collapse pages/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Site media" })).toHaveAttribute("href", "/admin/site-media");
    expect(screen.getByRole("link", { name: "Atelier" })).toHaveAttribute("href", "/admin/atelier");
    expect(screen.getByRole("link", { name: "Terms" })).toHaveAttribute("href", "/admin/terms");
    expect(screen.getByRole("link", { name: "Cookies" })).toHaveAttribute("href", "/admin/cookies");
    expect(screen.getByRole("link", { name: "Legal identity" })).toHaveAttribute("href", "/admin/legal");
    expect(screen.getByRole("link", { name: "FAQ" })).toHaveAttribute("href", "/admin/faq");

    await user.click(await screen.findByRole("button", { name: /expand atelier/i }));
    expect(screen.getByRole("link", { name: /01 · Atelier hero/ })).toHaveAttribute("href", "/admin/atelier?section=hero&part=content");
  });

  it("renders the store return button in the admin shell", () => {
    renderWithIntl(
      <AdminShell>
        <div>Admin content</div>
      </AdminShell>
    );

    const backToStore = screen.getByRole("link", { name: /back to shop/i });
    expect(backToStore).toHaveAttribute("href", "/");
    expect(screen.getByText("Menu")).toHaveClass("truncate");
    expect(screen.getByText("Atelier Marie")).toHaveClass("italic");
  });

  it("lists stock work directly under Stock and production", async () => {
    const user = userEvent.setup();
    renderWithIntl(<AdminSidebar />);

    await user.click(screen.getByRole("button", { name: /expand stock and production/i }));
    expect(screen.getByRole("button", { name: /collapse stock and production/i })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Stock" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Materials" })).toHaveAttribute("href", "/admin/inventory/materials");
  });

  it("collapses and expands inactive groups", async () => {
    const user = userEvent.setup();
    renderWithIntl(<AdminSidebar />);

    expect(screen.getByRole("link", { name: "Atelier" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /collapse pages/i }));
    expect(screen.queryByRole("link", { name: "Atelier" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /expand pages/i }));
    expect(screen.getByRole("link", { name: "Atelier" })).toBeInTheDocument();
  });
});
