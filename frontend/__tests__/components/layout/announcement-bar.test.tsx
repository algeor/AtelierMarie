import { screen, waitFor, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { renderWithIntl } from "../../test-utils";
import type { PublicBannerResponse } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  getPublicBanner: vi.fn(),
}));

import { getPublicBanner } from "@/lib/api";
import { AnnouncementBar } from "@/components/layout/AnnouncementBar";

const mockedGetPublicBanner = vi.mocked(getPublicBanner);

function bannerResponse(overrides = {}): PublicBannerResponse {
  return {
    banner: {
      message: "20% off spring candles",
      link_label: null,
      link_url: null,
      dismiss_key: "default:v2",
      ...overrides,
    },
  };
}

describe("AnnouncementBar (managed banner)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("renders the active managed banner message", async () => {
    mockedGetPublicBanner.mockResolvedValue(bannerResponse());
    renderWithIntl(<AnnouncementBar />);
    await waitFor(() => {
      expect(screen.getByText("20% off spring candles")).toBeInTheDocument();
    });
  });

  it("renders a link when configured", async () => {
    mockedGetPublicBanner.mockResolvedValue(
      bannerResponse({ link_url: "/products", link_label: "Shop now" })
    );
    renderWithIntl(<AnnouncementBar />);
    const link = await screen.findByText("Shop now");
    expect(link).toHaveAttribute("href", "/products");
  });

  it("does not render unsafe link schemes", async () => {
    mockedGetPublicBanner.mockResolvedValue(
      bannerResponse({ link_url: "javascript:alert(1)", link_label: "Shop now" })
    );
    renderWithIntl(<AnnouncementBar />);

    expect(await screen.findByText("20% off spring candles")).toBeInTheDocument();
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.queryByText("Shop now")).not.toBeInTheDocument();
  });

  it("renders nothing when no banner is active", async () => {
    mockedGetPublicBanner.mockResolvedValue({ banner: null });
    const { container } = renderWithIntl(<AnnouncementBar />);
    await waitFor(() => {
      expect(mockedGetPublicBanner).toHaveBeenCalled();
    });
    expect(container.querySelector("p")).toBeNull();
  });

  it("hides after dismissal and stays hidden for the same version", async () => {
    mockedGetPublicBanner.mockResolvedValue(bannerResponse({ dismiss_key: "default:v2" }));
    const { unmount } = renderWithIntl(<AnnouncementBar />);
    await screen.findByText("20% off spring candles");

    fireEvent.click(screen.getByLabelText("Dismiss announcement"));
    await waitFor(() => {
      expect(screen.queryByText("20% off spring candles")).not.toBeInTheDocument();
    });
    expect(localStorage.getItem("announcement_dismissed_key")).toBe("default:v2");
    unmount();

    // Same version → stays dismissed on re-mount.
    renderWithIntl(<AnnouncementBar />);
    await waitFor(() => expect(mockedGetPublicBanner).toHaveBeenCalledTimes(2));
    expect(screen.queryByText("20% off spring candles")).not.toBeInTheDocument();
  });

  it("reappears when the banner version changes", async () => {
    localStorage.setItem("announcement_dismissed_key", "default:v1");
    mockedGetPublicBanner.mockResolvedValue(bannerResponse({ dismiss_key: "default:v2" }));
    renderWithIntl(<AnnouncementBar />);
    // New dismiss_key (v2) doesn't match the stored v1 → banner shows again.
    expect(await screen.findByText("20% off spring candles")).toBeInTheDocument();
  });
});
