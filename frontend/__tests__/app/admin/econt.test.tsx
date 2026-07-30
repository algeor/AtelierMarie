import React from "react";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithIntl } from "../../test-utils";
import type { EcontSettingsResponse } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  getEcontSettings: vi.fn(),
  updateEcontSettings: vi.fn(),
  testEcontConnection: vi.fn(),
}));

import {
  getEcontSettings,
  testEcontConnection,
  updateEcontSettings,
} from "@/lib/api";
import AdminEcontSettingsPage from "@/app/[locale]/admin/econt/page";

const mockedGetEcontSettings = vi.mocked(getEcontSettings);
const mockedUpdateEcontSettings = vi.mocked(updateEcontSettings);
const mockedTestEcontConnection = vi.mocked(testEcontConnection);

const settings: EcontSettingsResponse = {
  enabled: false,
  environment: "demo",
  shop_id: "shop-1",
  credential_source: "env",
  sender_delivery_mode: "office",
  sender_office_code: "1127",
  sender_city: "Sofia",
  sender_post_code: "1000",
  sender_address: "Rakovski 100",
  sender_quarter: null,
  sender_street: "Rakovski",
  sender_num: "100",
  sender_other: null,
  default_pack_count: 1,
  shipment_description: "Atelier Marie order",
  declared_value_enabled: false,
  default_payment_side: "receiver",
  courier_currency: "EUR",
  currency_conversion_rate: null,
  office_locator_enabled: false,
  auto_confirm_on_label: false,
  auto_delivered_on_trace: false,
  base_url: "https://delivery-demo.econt.com/services/",
  office_locator_url: "https://delivery.econt.com/customer_info.php",
  office_locator_origins: ["https://delivery.econt.com"],
  secret_state: {
    credential_source: "env",
    private_key_configured: true,
    shop_id_configured: true,
    encryption_key_configured: false,
  },
  last_health_status: null,
  last_health_checked_at: null,
  last_health_error: null,
  updated_at: "2026-07-01T00:00:00Z",
};

describe("AdminEcontSettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state", () => {
    mockedGetEcontSettings.mockReturnValue(new Promise(() => {}));
    renderWithIntl(<AdminEcontSettingsPage />);

    expect(document.querySelectorAll("[aria-hidden='true']").length).toBeGreaterThan(0);
  });

  it("renders configured secret state without exposing raw secrets", async () => {
    mockedGetEcontSettings.mockResolvedValue(settings);
    renderWithIntl(<AdminEcontSettingsPage />);

    await waitFor(() => {
      expect(screen.getByText("Econt Settings")).toBeInTheDocument();
    });
    expect(screen.getAllByText("Configured").length).toBeGreaterThanOrEqual(2);
    expect(screen.queryByText(/private-demo-key/i)).not.toBeInTheDocument();
  });

  it("saves dirty non-secret settings", async () => {
    mockedGetEcontSettings.mockResolvedValue(settings);
    mockedUpdateEcontSettings.mockResolvedValue({ ...settings, shop_id: "shop-2" });
    const user = userEvent.setup();
    renderWithIntl(<AdminEcontSettingsPage />);

    const shopId = await screen.findByLabelText("Shop ID");
    await user.clear(shopId);
    await user.type(shopId, "shop-2");
    await user.click(screen.getByRole("button", { name: "Save settings" }));

    await waitFor(() => {
      expect(mockedUpdateEcontSettings).toHaveBeenCalledWith(
        expect.objectContaining({ shop_id: "shop-2" }),
      );
    });
    expect(await screen.findByText("Econt settings saved")).toBeInTheDocument();
  });

  it("shows validation errors before saving", async () => {
    mockedGetEcontSettings.mockResolvedValue(settings);
    const user = userEvent.setup();
    renderWithIntl(<AdminEcontSettingsPage />);

    const packCount = await screen.findByLabelText("Default package count");
    await user.clear(packCount);
    await user.type(packCount, "0");
    await user.click(screen.getByRole("button", { name: "Save settings" }));

    expect(await screen.findByText("Package count must be between 1 and 99")).toBeInTheDocument();
    expect(mockedUpdateEcontSettings).not.toHaveBeenCalled();
  });

  it("shows test connection outcome", async () => {
    mockedGetEcontSettings.mockResolvedValue(settings);
    mockedTestEcontConnection.mockResolvedValue({
      status: "missing_configuration",
      ok: false,
      message: "Missing Econt configuration",
      checked_at: "2026-07-01T00:00:00Z",
      details: null,
    });
    const user = userEvent.setup();
    renderWithIntl(<AdminEcontSettingsPage />);

    await user.click(await screen.findByRole("button", { name: "Test connection" }));

    expect(await screen.findByText(/Missing configuration: Missing Econt configuration/)).toBeInTheDocument();
  });
});
