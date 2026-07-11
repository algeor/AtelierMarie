import React from "react";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { renderWithIntl } from "../../test-utils";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/",
}));

const mockLogout = vi.fn();
const mockLogin = vi.fn();

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: {
      id: "user-001",
      email: "marie@ateliermarie.com",
      name: "Marie",
      avatar_url: "https://example.com/avatar.jpg",
      is_admin: false,
    },
    isAuthenticated: true,
    isLoading: false,
    error: null,
    login: mockLogin,
    logout: mockLogout,
    loginComplete: vi.fn(),
  }),
}));

import { UserMenu } from "@/components/auth/UserMenu";

describe("UserMenu", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders avatar when avatar_url is present", () => {
    renderWithIntl(<UserMenu />);
    const img = document.querySelector("img");
    expect(img).toHaveAttribute("src", "https://example.com/avatar.jpg");
  });

  it("opens dropdown on click", async () => {
    const user = userEvent.setup();
    renderWithIntl(<UserMenu />);

    const trigger = screen.getByRole("button", { expanded: false });
    await user.click(trigger);

    expect(screen.getByRole("menu")).toBeInTheDocument();
  });

  it("closes dropdown on second click", async () => {
    const user = userEvent.setup();
    renderWithIntl(<UserMenu />);

    const trigger = screen.getByRole("button");
    await user.click(trigger);
    expect(screen.getByRole("menu")).toBeInTheDocument();

    await user.click(trigger);
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("contains expected links", async () => {
    const user = userEvent.setup();
    renderWithIntl(<UserMenu />);

    await user.click(screen.getByRole("button"));

    expect(screen.getByRole("link", { name: "My Account" })).toHaveAttribute("href", "/account");
    expect(screen.getByRole("link", { name: "My Orders" })).toHaveAttribute("href", "/orders");
  });

  it("calls logout on Sign Out click", async () => {
    const user = userEvent.setup();
    renderWithIntl(<UserMenu />);

    await user.click(screen.getByRole("button"));
    await user.click(screen.getByRole("menuitem", { name: "Sign Out" }));

    expect(mockLogout).toHaveBeenCalled();
  });

  it("closes on Escape key", async () => {
    const user = userEvent.setup();
    renderWithIntl(<UserMenu />);

    await user.click(screen.getByRole("button"));
    expect(screen.getByRole("menu")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("has correct ARIA attributes", async () => {
    const user = userEvent.setup();
    renderWithIntl(<UserMenu />);

    const trigger = screen.getByRole("button");
    expect(trigger).toHaveAttribute("aria-haspopup", "menu");
    expect(trigger).toHaveAttribute("aria-expanded", "false");

    await user.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("menu")).toBeInTheDocument();
  });
});

describe("UserMenu with no avatar", () => {
  it("shows initial circle when avatar_url is null", async () => {
    vi.resetModules();
    vi.doMock("@/contexts/AuthContext", () => ({
      useAuth: () => ({
        user: {
          id: "user-001",
          email: "marie@ateliermarie.com",
          name: "Marie",
          avatar_url: null,
          is_admin: false,
        },
        isAuthenticated: true,
        isLoading: false,
        error: null,
        login: vi.fn(),
        logout: vi.fn(),
        loginComplete: vi.fn(),
      }),
    }));

    const { UserMenu: UserMenuNoAvatar } = await import("@/components/auth/UserMenu");
    const { renderWithIntl: renderWithFreshIntl } = await import("../../test-utils");
    const { screen: s } = await import("@testing-library/react");
    renderWithFreshIntl(<UserMenuNoAvatar />);
    expect(s.getByText("M")).toBeInTheDocument();
  });
});
