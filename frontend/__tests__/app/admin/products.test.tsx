import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";

const mockPush = vi.fn();
const mockReplace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  usePathname: () => "/admin/products",
  useParams: () => ({ id: "lavender-dreams-300ml" }),
}));

vi.mock("@/lib/api", () => ({
  getCurrentUser: vi.fn(),
  getAdminProducts: vi.fn(),
  getAdminProduct: vi.fn(),
  updateProduct: vi.fn(),
  createProduct: vi.fn(),
}));

import {
  getCurrentUser,
  getAdminProducts,
  getAdminProduct,
  updateProduct,
  createProduct,
} from "@/lib/api";
import type { ProductListResponse, ProductResponse, UserResponse } from "@/lib/types";

const mockedGetCurrentUser = vi.mocked(getCurrentUser);
const mockedGetAdminProducts = vi.mocked(getAdminProducts);
const mockedGetAdminProduct = vi.mocked(getAdminProduct);
const mockedUpdateProduct = vi.mocked(updateProduct);
const mockedCreateProduct = vi.mocked(createProduct);

const ADMIN_USER: UserResponse = {
  id: "user-001",
  email: "marie@ateliermarie.com",
  name: "Marie",
  avatar_url: null,
  is_admin: true,
};

const MOCK_PRODUCT: ProductResponse = {
  id: "lavender-dreams-300ml",
  name: "Lavender Dreams",
  description: "Hand-poured soy candle",
  materials: "Soy wax, lavender oil",
  days_to_craft: 3,
  price_cents: 3200,
  category: "Floral",
  image_url: null,
  stock: 24,
  is_active: true,
  is_featured: true,
  created_at: "2024-06-01T10:00:00Z",
  updated_at: "2024-06-01T10:00:00Z",
};

const MOCK_PRODUCT_INACTIVE: ProductResponse = {
  ...MOCK_PRODUCT,
  id: "vanilla-bourbon-300ml",
  name: "Vanilla Bourbon",
  price_cents: 3800,
  is_active: false,
  stock: 0,
};

const MOCK_PRODUCT_LIST: ProductListResponse = {
  products: [MOCK_PRODUCT, MOCK_PRODUCT_INACTIVE],
  total: 2,
  page: 1,
  limit: 100,
};

describe("Admin Products List", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetCurrentUser.mockResolvedValue(ADMIN_USER);
  });

  it("renders product table with data", async () => {
    mockedGetAdminProducts.mockResolvedValue(MOCK_PRODUCT_LIST);

    const { AdminProvider } = await import("@/contexts/AdminContext");
    const { AdminGuard } = await import("@/components/admin/AdminGuard");
    const AdminProductsPage = (await import("@/app/admin/products/page")).default;

    render(
      <AdminProvider>
        <AdminGuard>
          <AdminProductsPage />
        </AdminGuard>
      </AdminProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Lavender Dreams")).toBeInTheDocument();
      expect(screen.getByText("Vanilla Bourbon")).toBeInTheDocument();
    });

    expect(screen.getByText("€32.00")).toBeInTheDocument();
    expect(screen.getByText("€38.00")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("Inactive")).toBeInTheDocument();
  });

  it("shows Create Product button", async () => {
    mockedGetAdminProducts.mockResolvedValue(MOCK_PRODUCT_LIST);

    const { AdminProvider } = await import("@/contexts/AdminContext");
    const { AdminGuard } = await import("@/components/admin/AdminGuard");
    const AdminProductsPage = (await import("@/app/admin/products/page")).default;

    render(
      <AdminProvider>
        <AdminGuard>
          <AdminProductsPage />
        </AdminGuard>
      </AdminProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Create Product")).toBeInTheDocument();
    });
  });

  it("toggles product active status", async () => {
    mockedGetAdminProducts.mockResolvedValue(MOCK_PRODUCT_LIST);
    mockedUpdateProduct.mockResolvedValue({ ...MOCK_PRODUCT, is_active: false });

    const { AdminProvider } = await import("@/contexts/AdminContext");
    const { AdminGuard } = await import("@/components/admin/AdminGuard");
    const AdminProductsPage = (await import("@/app/admin/products/page")).default;

    render(
      <AdminProvider>
        <AdminGuard>
          <AdminProductsPage />
        </AdminGuard>
      </AdminProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Lavender Dreams")).toBeInTheDocument();
    });

    const deactivateButtons = screen.getAllByText("Deactivate");
    fireEvent.click(deactivateButtons[0]);

    await waitFor(() => {
      expect(mockedUpdateProduct).toHaveBeenCalledWith("lavender-dreams-300ml", {
        is_active: false,
      });
    });
  });
});

describe("Admin Product Form Validation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetCurrentUser.mockResolvedValue(ADMIN_USER);
  });

  it("shows validation errors for empty required fields", async () => {
    const { AdminProvider } = await import("@/contexts/AdminContext");
    const { AdminGuard } = await import("@/components/admin/AdminGuard");
    const CreateProductPage = (await import("@/app/admin/products/new/page")).default;

    render(
      <AdminProvider>
        <AdminGuard>
          <CreateProductPage />
        </AdminGuard>
      </AdminProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Create Product", { selector: "h1" })).toBeInTheDocument();
    });

    const submitButton = screen.getByRole("button", { name: "Create Product" });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText("Name is required")).toBeInTheDocument();
      expect(screen.getByText("Product ID is required")).toBeInTheDocument();
      expect(screen.getByText("Category is required")).toBeInTheDocument();
    });

    expect(mockedCreateProduct).not.toHaveBeenCalled();
  });

  it("pre-fills form when editing existing product", async () => {
    mockedGetAdminProduct.mockResolvedValue(MOCK_PRODUCT);

    const { AdminProvider } = await import("@/contexts/AdminContext");
    const { AdminGuard } = await import("@/components/admin/AdminGuard");
    const EditProductPage = (await import("@/app/admin/products/[id]/edit/page")).default;

    render(
      <AdminProvider>
        <AdminGuard>
          <EditProductPage />
        </AdminGuard>
      </AdminProvider>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue("Lavender Dreams")).toBeInTheDocument();
      expect(screen.getByDisplayValue("32.00")).toBeInTheDocument();
    });
  });
});
