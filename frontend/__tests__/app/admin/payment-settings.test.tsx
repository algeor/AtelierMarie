import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithIntl } from "../../test-utils";
import AdminPaymentSettingsPage from "@/app/[locale]/admin/settings/payments/page";
import { ApiError } from "@/lib/api-client";
import type { PaymentSettingsResponse } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  getAdminPaymentSettings: vi.fn(),
  updateAdminPaymentSettings: vi.fn(),
}));

import { getAdminPaymentSettings, updateAdminPaymentSettings } from "@/lib/api";

const mockedGetSettings = vi.mocked(getAdminPaymentSettings);
const mockedUpdateSettings = vi.mocked(updateAdminPaymentSettings);

const DEFAULT_SETTINGS: PaymentSettingsResponse = {
  card_payments_enabled: true,
  pay_on_delivery_enabled: true,
  pay_on_delivery_max_cents: 5000,
  stripe: {
    mode: "test",
    secret_key_configured: true,
    webhook_secret_configured: false,
    publishable_key_configured: true,
    ready_for_card_payments: false,
    problems: ["Webhook secret is missing"],
  },
};

describe("Admin payment settings page", () => {
  beforeEach(() => {
    mockedGetSettings.mockReset();
    mockedUpdateSettings.mockReset();
    mockedGetSettings.mockResolvedValue(DEFAULT_SETTINGS);
    mockedUpdateSettings.mockImplementation(async (data) => ({
      ...DEFAULT_SETTINGS,
      ...data,
      stripe: DEFAULT_SETTINGS.stripe,
    }));
  });

  it("shows Stripe health and saves payment method settings", async () => {
    renderWithIntl(<AdminPaymentSettingsPage />);

    expect(
      await screen.findByRole("heading", { name: "Payment settings", level: 1 })
    ).toBeInTheDocument();
    expect(screen.getByText("Test")).toBeInTheDocument();
    expect(screen.getByText("Not ready")).toBeInTheDocument();
    expect(screen.getByText("Webhook secret is missing")).toBeInTheDocument();

    const codToggle = screen.getByLabelText(/Pay on delivery/) as HTMLInputElement;
    expect(codToggle.checked).toBe(true);

    fireEvent.click(codToggle);
    fireEvent.change(screen.getByLabelText("Pay-on-delivery max amount"), {
      target: { value: "25.50" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(mockedUpdateSettings).toHaveBeenCalledWith({
        card_payments_enabled: true,
        pay_on_delivery_enabled: false,
        pay_on_delivery_max_cents: 2550,
      }),
    );
    expect(await screen.findByText("Payment settings saved.")).toBeInTheDocument();
  });

  it("rejects saving when both payment methods are disabled", async () => {
    renderWithIntl(<AdminPaymentSettingsPage />);

    const cardToggle = (await screen.findByLabelText(/Card payments/)) as HTMLInputElement;
    const codToggle = screen.getByLabelText(/Pay on delivery/) as HTMLInputElement;

    fireEvent.click(cardToggle);
    fireEvent.click(codToggle);
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("At least one payment method must be enabled.")).toBeInTheDocument();
    expect(mockedUpdateSettings).not.toHaveBeenCalled();
  });

  it("surfaces backend validation errors", async () => {
    mockedUpdateSettings.mockRejectedValue(
      new ApiError({
        error: {
          code: "PAYMENT_SETTINGS_INVALID",
          message: "Live Stripe keys are required in production",
          details: null,
        },
      }),
    );

    renderWithIntl(<AdminPaymentSettingsPage />);

    const codToggle = (await screen.findByLabelText(/Pay on delivery/)) as HTMLInputElement;
    fireEvent.click(codToggle);
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Live Stripe keys are required in production")).toBeInTheDocument();
  });
});
