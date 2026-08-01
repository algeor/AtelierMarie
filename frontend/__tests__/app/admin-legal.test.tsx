import React from "react";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithIntl } from "../test-utils";

const api = vi.hoisted(() => ({
  getAccountingConfig: vi.fn(),
  createSellerLegalProfile: vi.fn(),
}));

vi.mock("@/lib/api", () => api);

import AdminLegalPage from "@/app/[locale]/admin/legal/page";

describe("Admin legal identity page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getAccountingConfig.mockResolvedValue({
      seller_profile: {
        id: 1,
        effective_date: "2026-08-01",
        reviewed: true,
        company_display_name: "Atelier Marie",
        legal_name: "Atelier Marie OOD",
        uic_eik: "123456789",
        vat_identification_number: "BG123456789",
        registered_address: {
          line1: "1 Candle Street",
          city: "Sofia",
          postal_code: "1000",
          country: "Bulgaria",
        },
        contact_email: "contacts@theateliermarie.com",
        bank_details_configured: false,
        default_currency: "EUR",
        created_at: "2026-08-01T10:00:00Z",
      },
    });
    api.createSellerLegalProfile.mockResolvedValue({});
  });

  it("loads, previews, and saves public legal identity", async () => {
    renderWithIntl(<AdminLegalPage />);

    expect(await screen.findByRole("heading", { name: "Legal identity" })).toBeInTheDocument();
    expect(screen.getByDisplayValue("Atelier Marie OOD")).toBeInTheDocument();
    expect(screen.getByText("1 Candle Street, 1000 Sofia, Bulgaria")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Legal name"), {
      target: { value: "Atelier Marie EOOD" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(api.createSellerLegalProfile).toHaveBeenCalledWith(
        expect.objectContaining({
          legal_name: "Atelier Marie EOOD",
          uic_eik: "123456789",
          registered_address: expect.objectContaining({ line1: "1 Candle Street" }),
        })
      );
    });
  });
});
