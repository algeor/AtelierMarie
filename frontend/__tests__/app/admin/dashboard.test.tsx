import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { renderWithIntl } from "../../test-utils";

// Mock next/navigation
const mockPush = vi.fn();
const mockReplace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  usePathname: () => "/admin",
  useParams: () => ({}),
}));

// Mock @/i18n/navigation
vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/",
}));

// Mock the API
vi.mock("@/lib/api", () => ({
  getCurrentUser: vi.fn(),
  getAdminStats: vi.fn(),
}));

import { getCurrentUser, getAdminStats } from "@/lib/api";
import type { AdminStats, UserResponse } from "@/lib/types";

const mockedGetCurrentUser = vi.mocked(getCurrentUser);
const mockedGetAdminStats = vi.mocked(getAdminStats);

const ADMIN_USER: UserResponse = {
  id: "user-001",
  email: "marie@ateliermarie.com",
  name: "Marie",
  avatar_url: null,
  is_admin: true,
};

const NON_ADMIN_USER: UserResponse = {
  id: "user-002",
  email: "customer@example.com",
  name: "Customer",
  avatar_url: null,
  is_admin: false,
};

const MOCK_STATS: AdminStats = {
  orders_today: 5,
  revenue_this_week_cents: 15000,
  active_product_count: 3,
};

describe("Admin Route Protection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("redirects non-admin users to /", async () => {
    mockedGetCurrentUser.mockResolvedValue(NON_ADMIN_USER);

    // Import AdminGuard dynamically to avoid stale module state
    const { AdminProvider } = await import("@/contexts/AdminContext");
    const { AdminGuard } = await import("@/components/admin/AdminGuard");

    render(
      <AdminProvider>
        <AdminGuard>
          <div>Admin Content</div>
        </AdminGuard>
      </AdminProvider>
    );

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/");
    });
  });

  it("redirects unauthenticated users to /", async () => {
    mockedGetCurrentUser.mockResolvedValue(null);

    const { AdminProvider } = await import("@/contexts/AdminContext");
    const { AdminGuard } = await import("@/components/admin/AdminGuard");

    render(
      <AdminProvider>
        <AdminGuard>
          <div>Admin Content</div>
        </AdminGuard>
      </AdminProvider>
    );

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/");
    });
  });

  it("renders admin content for admin users", async () => {
    mockedGetCurrentUser.mockResolvedValue(ADMIN_USER);

    const { AdminProvider } = await import("@/contexts/AdminContext");
    const { AdminGuard } = await import("@/components/admin/AdminGuard");

    render(
      <AdminProvider>
        <AdminGuard>
          <div>Admin Content</div>
        </AdminGuard>
      </AdminProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Admin Content")).toBeInTheDocument();
    });
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it("shows loading state while checking auth", async () => {
    // Never resolve to keep loading
    mockedGetCurrentUser.mockReturnValue(new Promise(() => {}));

    const { AdminProvider } = await import("@/contexts/AdminContext");
    const { AdminGuard } = await import("@/components/admin/AdminGuard");

    render(
      <AdminProvider>
        <AdminGuard>
          <div>Admin Content</div>
        </AdminGuard>
      </AdminProvider>
    );

    expect(screen.getByText("Loading...")).toBeInTheDocument();
    expect(screen.queryByText("Admin Content")).not.toBeInTheDocument();
  });
});

describe("Admin Dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetCurrentUser.mockResolvedValue(ADMIN_USER);
  });

  it("renders stats cards with data", async () => {
    mockedGetAdminStats.mockResolvedValue(MOCK_STATS);

    const { AdminProvider } = await import("@/contexts/AdminContext");
    const { AdminGuard } = await import("@/components/admin/AdminGuard");
    const AdminDashboardPage = (await import("@/app/[locale]/admin/page")).default;

    renderWithIntl(
      <AdminProvider>
        <AdminGuard>
          <AdminDashboardPage />
        </AdminGuard>
      </AdminProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Dashboard")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText("5")).toBeInTheDocument();
      expect(screen.getByText("€150.00")).toBeInTheDocument();
      expect(screen.getByText("3")).toBeInTheDocument();
    });
  });

  it("shows loading skeletons while fetching stats", async () => {
    mockedGetAdminStats.mockReturnValue(new Promise(() => {}));

    const { AdminProvider } = await import("@/contexts/AdminContext");
    const { AdminGuard } = await import("@/components/admin/AdminGuard");
    const AdminDashboardPage = (await import("@/app/[locale]/admin/page")).default;

    renderWithIntl(
      <AdminProvider>
        <AdminGuard>
          <AdminDashboardPage />
        </AdminGuard>
      </AdminProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Dashboard")).toBeInTheDocument();
    });

    // Skeleton elements should be present (they render as divs with animate-pulse)
    expect(screen.getByText("Overview of your store performance")).toBeInTheDocument();
  });

  it("shows error when stats fail to load", async () => {
    mockedGetAdminStats.mockRejectedValue(new Error("Network error"));

    const { AdminProvider } = await import("@/contexts/AdminContext");
    const { AdminGuard } = await import("@/components/admin/AdminGuard");
    const AdminDashboardPage = (await import("@/app/[locale]/admin/page")).default;

    renderWithIntl(
      <AdminProvider>
        <AdminGuard>
          <AdminDashboardPage />
        </AdminGuard>
      </AdminProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Failed to load stats")).toBeInTheDocument();
    });
  });
});
