/**
 * DeliverySection — Econt door-delivery place picker.
 *
 * Focus: the Econt-only served-place typeahead that autofills a read-only
 * postcode so ambiguous same-named towns (three "Садово") price live instead
 * of degrading to the flat fallback. Uses the real message files + next-intl
 * so the picker's labels/placeholders render exactly as in production.
 */
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { NextIntlClientProvider } from "next-intl";
import enMessages from "@/messages/en.json";
import type { CityPlace } from "@/lib/types";

const getDeliveryPlaces = vi.fn();

vi.mock("@/lib/api", () => ({
  getDeliveryCities: vi.fn(async () => []),
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

function renderSection(value: Partial<DeliveryInfo>, onChange = vi.fn()) {
  render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <DeliverySection value={value} onChange={onChange} />
    </NextIntlClientProvider>,
  );
  return onChange;
}

// Econt + door already selected, so the place picker is the visible sub-form.
const ECONT_DOOR: Partial<DeliveryInfo> = {
  method: "door",
  door: { courier: "econt" } as DeliveryInfo["door"],
};

describe("DeliverySection — Econt door place picker", () => {
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

  it("keeps a free-text (editable) postcode for Speedy door delivery", () => {
    renderSection({
      method: "door",
      door: { courier: "speedy", city: "София", postal_code: "1000" } as DeliveryInfo["door"],
    });

    // Speedy has no served-places source, so the picker is not used and the
    // postcode stays editable.
    const postal = screen.getByDisplayValue("1000") as HTMLInputElement;
    expect(postal.readOnly).toBe(false);
    expect(getDeliveryPlaces).not.toHaveBeenCalled();
  });
});
