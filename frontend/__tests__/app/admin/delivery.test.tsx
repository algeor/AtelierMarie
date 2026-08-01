import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithIntl } from "../../test-utils";
import AdminDeliveryPage from "@/app/[locale]/admin/delivery/page";
import type { DeliverySettingsResponse } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  getAdminDeliverySettings: vi.fn(),
  updateAdminDeliverySettings: vi.fn(),
}));

import { getAdminDeliverySettings, updateAdminDeliverySettings } from "@/lib/api";

const mockedGetSettings = vi.mocked(getAdminDeliverySettings);
const mockedUpdateSettings = vi.mocked(updateAdminDeliverySettings);

const DEFAULT_SETTINGS: DeliverySettingsResponse = {
  speedy_office_enabled: true,
  speedy_door_enabled: true,
  econt_office_enabled: true,
  econt_door_enabled: true,
  cod_enabled: true,
  card_enabled: true,
  bank_transfer_enabled: true,
  updated_at: "2026-07-31 12:00:00",
};

describe("Admin delivery settings page", () => {
  beforeEach(() => {
    mockedGetSettings.mockReset();
    mockedUpdateSettings.mockReset();
    mockedGetSettings.mockResolvedValue(DEFAULT_SETTINGS);
    mockedUpdateSettings.mockImplementation(async (data) => ({
      ...data,
      updated_at: "2026-07-31 12:05:00",
    }));
  });

  it("saves courier/method availability toggles", async () => {
    renderWithIntl(<AdminDeliveryPage />);

    expect(
      await screen.findByRole("heading", { name: "Delivery and payment methods", level: 1 }),
    ).toBeInTheDocument();
    expect(screen.getByText("Shipping price calculation")).toBeInTheDocument();

    const speedyDoor = screen.getByLabelText(/Speedy.*Door delivery/) as HTMLInputElement;
    expect(speedyDoor.checked).toBe(true);

    fireEvent.click(speedyDoor);
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(mockedUpdateSettings).toHaveBeenCalledWith({
        speedy_office_enabled: true,
        speedy_door_enabled: false,
        econt_office_enabled: true,
        econt_door_enabled: true,
        cod_enabled: true,
        card_enabled: true,
        bank_transfer_enabled: true,
      }),
    );
    expect(await screen.findByText("Delivery settings saved.")).toBeInTheDocument();
  });

  it("saves payment availability toggles", async () => {
    renderWithIntl(<AdminDeliveryPage />);

    const card = await screen.findByLabelText(/Card payment/);
    expect((card as HTMLInputElement).checked).toBe(true);

    fireEvent.click(card);
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(mockedUpdateSettings).toHaveBeenCalledWith({
        speedy_office_enabled: true,
        speedy_door_enabled: true,
        econt_office_enabled: true,
        econt_door_enabled: true,
        cod_enabled: true,
        card_enabled: false,
        bank_transfer_enabled: true,
      }),
    );
  });
});
