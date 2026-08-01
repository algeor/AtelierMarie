/**
 * DeliverySection — courier door-delivery place picker.
 *
 * Focus: the served-place typeahead that autofills a read-only
 * postcode so ambiguous same-named towns (three "Садово") price live instead
 * of degrading to the flat fallback. Uses the real message files + next-intl
 * so the picker's labels/placeholders render exactly as in production.
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { NextIntlClientProvider } from "next-intl";
import enMessages from "@/messages/en.json";
import type { CityPlace, DeliverySettingsResponse } from "@/lib/types";

const getDeliveryPlaces = vi.fn();

vi.mock("@/lib/api", () => ({
  getDeliveryCities: vi.fn(async () => []),
  getDeliveryConfig: vi.fn(async () => ({
    econt: {
      office_locator_enabled: false,
      office_locator_url: "https://delivery.econt.com/customer_info.php",
      office_locator_origins: ["https://delivery.econt.com"],
    },
  })),
  getDeliveryOffices: vi.fn(async () => []),
  getDeliveryPlaces: (...args: unknown[]) => getDeliveryPlaces(...args),
}));

import { DeliverySection } from "@/components/checkout/DeliverySection";
import type { DeliveryInfo } from "@/lib/types";

// The three ambiguous "Садово" places — same name, distinct region + postcode.
const SADOVO_PLACES: CityPlace[] = [
  { name: "Садово", region: "Пловдив", postal_code: "4122" },
  { name: "Садово", region: "Благоевград", postal_code: "2922" },
  { name: "Садово", region: "Бургас", postal_code: "8463" },
];

function renderSection(
  value: Partial<DeliveryInfo>,
  onChange = vi.fn(),
  deliverySettings?: DeliverySettingsResponse,
) {
  render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <DeliverySection value={value} onChange={onChange} deliverySettings={deliverySettings} />
    </NextIntlClientProvider>,
  );
  return onChange;
}

const ALL_ENABLED: DeliverySettingsResponse = {
  speedy_office_enabled: true,
  speedy_door_enabled: true,
  econt_office_enabled: true,
  econt_door_enabled: true,
  cod_enabled: true,
  card_enabled: true,
  bank_transfer_enabled: true,
  updated_at: "2026-07-31 12:00:00",
};

// Door already selected, so the place picker is the visible sub-form.
const ECONT_DOOR: Partial<DeliveryInfo> = {
  method: "door",
  door: { courier: "econt" } as DeliveryInfo["door"],
};

const SPEEDY_DOOR: Partial<DeliveryInfo> = {
  method: "door",
  door: { courier: "speedy" } as DeliveryInfo["door"],
};

describe("DeliverySection — courier door place picker", () => {
  beforeEach(() => {
    getDeliveryPlaces.mockReset();
    getDeliveryPlaces.mockResolvedValue(SADOVO_PLACES);
  });

  it("shows ambiguous same-named places as distinct 'name — region' rows", async () => {
    renderSection(ECONT_DOOR);

    const cityInput = screen.getByPlaceholderText("e.g., Sofia");
    fireEvent.change(cityInput, { target: { value: "Садо" } });

    await waitFor(() => expect(getDeliveryPlaces).toHaveBeenCalledWith("econt", "Садо", "en"));

    // All three regions appear — the picker does not collapse ambiguous names.
    await screen.findByText("Садово — Пловдив");
    expect(screen.getByText("Садово — Благоевград")).toBeInTheDocument();
    expect(screen.getByText("Садово — Бургас")).toBeInTheDocument();
  });

  it("autofills a read-only postcode from the selected place", async () => {
    const onChange = renderSection(ECONT_DOOR);

    const cityInput = screen.getByPlaceholderText("e.g., Sofia");
    fireEvent.change(cityInput, { target: { value: "Садо" } });

    const plovdivRow = await screen.findByText("Садово — Пловдив");
    fireEvent.click(plovdivRow);

    // Selecting the place patches the door with city + its postcode.
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        door: expect.objectContaining({ city: "Садово", postal_code: "4122" }),
      }),
    );
  });

  it("renders the postcode field read-only for Econt door delivery", () => {
    // Postcode already filled (as it would be after a place selection).
    renderSection({
      method: "door",
      door: { courier: "econt", city: "Садово", postal_code: "4122" } as DeliveryInfo["door"],
    });

    const postal = screen.getByDisplayValue("4122") as HTMLInputElement;
    expect(postal.readOnly).toBe(true);
  });

  it("uses the same place picker and postcode autofill for Speedy door delivery", async () => {
    getDeliveryPlaces.mockResolvedValue([
      { name: "София", region: "София (столица)", postal_code: "1000" },
    ]);
    const onChange = renderSection(SPEEDY_DOOR);

    const cityInput = screen.getByPlaceholderText("e.g., Sofia");
    fireEvent.change(cityInput, { target: { value: "Соф" } });

    await waitFor(() => expect(getDeliveryPlaces).toHaveBeenCalledWith("speedy", "Соф", "en"));

    const sofiaRow = await screen.findByText("София — София (столица)");
    fireEvent.click(sofiaRow);

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        door: expect.objectContaining({ city: "София", postal_code: "1000" }),
      }),
    );
  });

  it("renders the postcode field read-only for Speedy door delivery", () => {
    renderSection({
      method: "door",
      door: { courier: "speedy", city: "София", postal_code: "1000" } as DeliveryInfo["door"],
    });

    const postal = screen.getByDisplayValue("1000") as HTMLInputElement;
    expect(postal.readOnly).toBe(true);
  });

  it("programmatically labels door delivery fields with visible labels", () => {
    renderSection({
      method: "door",
      door: { courier: "speedy" } as DeliveryInfo["door"],
    });

    expect(screen.getByLabelText("City *")).toHaveAttribute("id", "delivery-door-city");
    expect(screen.getByLabelText("Postal code *")).toHaveAttribute("id", "delivery-door-postal-code");
    expect(screen.getByLabelText("Street and number *")).toHaveAttribute("id", "delivery-door-street");
    expect(screen.getByLabelText("Building / Entrance (optional)")).toHaveAttribute("id", "delivery-door-building");
    expect(screen.getByLabelText("Floor / Apartment (optional)")).toHaveAttribute("id", "delivery-door-apartment");
  });

  it("associates validation errors with the affected door fields", () => {
    render(
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <DeliverySection
          value={{ method: "door", door: { courier: "speedy" } as DeliveryInfo["door"] }}
          onChange={vi.fn()}
          errors={{ city: "City is required", postalCode: "Postal code is required", street: "Street is required", phone: "Phone number is required" }}
        />
      </NextIntlClientProvider>,
    );

    expect(screen.getByLabelText("City *")).toHaveAccessibleDescription("City is required");
    expect(screen.getByLabelText("Postal code *")).toHaveAccessibleDescription("Postal code is required");
    expect(screen.getByLabelText("Street and number *")).toHaveAccessibleDescription("Street is required");
  });

  it("allows manual postcode entry when a Speedy place has no postcode", async () => {
    getDeliveryPlaces.mockResolvedValue([
      { name: "Батак", region: null, postal_code: null },
    ]);
    const onChange = renderSection(SPEEDY_DOOR);

    const cityInput = screen.getByPlaceholderText("e.g., Sofia");
    fireEvent.change(cityInput, { target: { value: "Бат" } });

    const batakRow = await screen.findByText("Батак");
    fireEvent.click(batakRow);

    const postal = screen.getByPlaceholderText("1000") as HTMLInputElement;
    expect(postal.readOnly).toBe(false);
    fireEvent.change(postal, { target: { value: "4580" } });

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        door: expect.objectContaining({ postal_code: "4580" }),
      }),
    );
  });

  it("hides a disabled courier for the selected delivery method", () => {
    renderSection(ECONT_DOOR, vi.fn(), {
      ...ALL_ENABLED,
      speedy_door_enabled: false,
    });

    expect(screen.queryByText("Speedy")).not.toBeInTheDocument();
    expect(screen.getByText("Econt")).toBeInTheDocument();
  });

  it("repairs a stale courier selection when settings disable it", async () => {
    const onChange = renderSection(SPEEDY_DOOR, vi.fn(), {
      ...ALL_ENABLED,
      speedy_door_enabled: false,
    });

    await waitFor(() =>
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          door: expect.objectContaining({ courier: "econt" }),
          office: null,
        }),
      ),
    );
  });

  it("hides a delivery method when no courier supports it", () => {
    renderSection({}, vi.fn(), {
      ...ALL_ENABLED,
      speedy_office_enabled: false,
      econt_office_enabled: false,
    });

    expect(screen.queryByText("Pick up from office")).not.toBeInTheDocument();
    expect(screen.getByText("Door delivery")).toBeInTheDocument();
  });
});
