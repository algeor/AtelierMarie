import React from "react";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { renderWithIntl } from "../../test-utils";
import type { DeliveryInfo, OfficeResponse } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  getDeliveryCities: vi.fn(),
  getDeliveryConfig: vi.fn(),
  getDeliveryOffices: vi.fn(),
}));

import { getDeliveryCities, getDeliveryConfig, getDeliveryOffices } from "@/lib/api";
import {
  DeliverySection,
  normalizeEcontLocatorOfficeMessage,
} from "@/components/checkout/DeliverySection";

const mockedGetDeliveryCities = vi.mocked(getDeliveryCities);
const mockedGetDeliveryConfig = vi.mocked(getDeliveryConfig);
const mockedGetDeliveryOffices = vi.mocked(getDeliveryOffices);

const econtValue: Partial<DeliveryInfo> = {
  method: "office",
  office: {
    courier: "econt",
    office_id: "",
    office_code: null,
    office_name: "",
    office_type: "office",
    phone: "+359888123456",
  },
  door: null,
};

const econtOffice: OfficeResponse = {
  id: "econt-1029",
  code: "1127",
  name: "Econt Sofia Center",
  type: "office",
  city: "Sofia",
  address: "Rakovski 100",
  working_hours: "Mon-Fri 09:00-18:00",
};

function mockDeliveryConfig(enabled = false) {
  mockedGetDeliveryConfig.mockResolvedValue({
    econt: {
      office_locator_enabled: enabled,
      office_locator_url: "https://delivery.econt.com/customer_info.php",
      office_locator_origins: ["https://delivery.econt.com"],
    },
  });
}

function renderDeliverySection(onChange = vi.fn(), value = econtValue) {
  mockDeliveryConfig(process.env.NEXT_PUBLIC_ECONT_OFFICE_LOCATOR_ENABLED === "true");
  renderWithIntl(<DeliverySection value={value} onChange={onChange} />);
  return onChange;
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.clearAllMocks();
});

describe("DeliverySection Econt office selection", () => {
  it("submits the Econt office code from the static picker", async () => {
    vi.stubEnv("NEXT_PUBLIC_ECONT_OFFICE_LOCATOR_ENABLED", "false");
    mockedGetDeliveryCities.mockResolvedValue(["Sofia"]);
    mockedGetDeliveryOffices.mockResolvedValue([econtOffice]);
    const user = userEvent.setup();
    const onChange = renderDeliverySection();

    await user.type(screen.getByPlaceholderText("Search city..."), "Sof");
    await waitFor(() => expect(mockedGetDeliveryCities).toHaveBeenCalledWith("econt", "Sof"));
    await user.click(screen.getByRole("button", { name: "Sofia" }));
    await user.click(await screen.findByRole("button", { name: /Econt Sofia Center/i }));

    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        office: expect.objectContaining({
          office_id: "econt-1029",
          office_code: "1127",
          phone: "+359888123456",
        }),
      }),
    );
  });

  it("normalizes Econt locator messages into the office schema", () => {
    const office = normalizeEcontLocatorOfficeMessage({
      office: {
        id: 1029,
        code: "1127",
        name: "Econt Sofia Center",
        type: "office",
        address: { city: "Sofia", fullAddress: "Rakovski 100" },
        workingHours: "Mon-Fri 09:00-18:00",
      },
    });

    expect(office).toEqual({
      id: "econt-1029",
      code: "1127",
      name: "Econt Sofia Center",
      type: "office",
      city: "Sofia",
      address: "Rakovski 100",
      working_hours: "Mon-Fri 09:00-18:00",
    });
  });

  it("uses public delivery config to enable the Econt locator", async () => {
    mockDeliveryConfig(true);
    renderWithIntl(<DeliverySection value={econtValue} onChange={vi.fn()} />);

    expect(await screen.findByTitle("Choose an Econt office")).toBeInTheDocument();
  });

  it("keeps static search when public delivery config disables the Econt locator", async () => {
    vi.stubEnv("NEXT_PUBLIC_ECONT_OFFICE_LOCATOR_ENABLED", "true");
    mockDeliveryConfig(false);
    renderWithIntl(<DeliverySection value={econtValue} onChange={vi.fn()} />);

    expect(await screen.findByPlaceholderText("Search city...")).toBeInTheDocument();
    expect(screen.queryByTitle("Choose an Econt office")).not.toBeInTheDocument();
  });

  it("ignores locator messages from unknown origins", async () => {
    vi.stubEnv("NEXT_PUBLIC_ECONT_OFFICE_LOCATOR_ENABLED", "true");
    vi.stubEnv("NEXT_PUBLIC_ECONT_OFFICE_LOCATOR_URL", "https://delivery.econt.com/customer_info.php");
    vi.stubEnv("NEXT_PUBLIC_ECONT_OFFICE_LOCATOR_ORIGINS", "https://delivery.econt.com");
    const onChange = renderDeliverySection();

    expect(await screen.findByTitle("Choose an Econt office")).toBeInTheDocument();
    fireEvent(
      window,
      new MessageEvent("message", {
        origin: "https://unknown.example",
        data: { office: econtOffice },
      }),
    );

    expect(onChange).not.toHaveBeenCalled();

    fireEvent(
      window,
      new MessageEvent("message", {
        origin: "https://delivery.econt.com",
        data: { office: econtOffice },
      }),
    );

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          office: expect.objectContaining({ office_code: "1127" }),
        }),
      );
    });
  });

  it("falls back to static search without clearing form data", async () => {
    vi.stubEnv("NEXT_PUBLIC_ECONT_OFFICE_LOCATOR_ENABLED", "true");
    mockedGetDeliveryCities.mockResolvedValue(["Sofia"]);
    mockedGetDeliveryOffices.mockResolvedValue([econtOffice]);
    const user = userEvent.setup();
    const onChange = renderDeliverySection();

    await user.click(await screen.findByRole("button", { name: "Use city search" }));
    await user.type(await screen.findByPlaceholderText("Search city..."), "Sof");
    await user.click(await screen.findByRole("button", { name: "Sofia" }));
    await user.click(await screen.findByRole("button", { name: /Econt Sofia Center/i }));

    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        office: expect.objectContaining({
          office_code: "1127",
          phone: "+359888123456",
        }),
      }),
    );
  });
});
