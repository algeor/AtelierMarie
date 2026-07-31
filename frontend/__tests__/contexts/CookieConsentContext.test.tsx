import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CookieConsentProvider } from "@/contexts/CookieConsentContext";
import { renderWithIntl } from "../test-utils";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, className }: { children: React.ReactNode; href: string; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
  usePathname: () => "/",
}));

describe("CookieConsentProvider", () => {
  beforeEach(() => {
    document.cookie = "atelier_cookie_consent=; Max-Age=0; Path=/";
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 200 })));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("shows the popup without consent and hides after necessary-only choice", async () => {
    renderWithIntl(
      <CookieConsentProvider>
        <div>Storefront</div>
      </CookieConsentProvider>
    );

    expect(screen.getByRole("region", { name: "Cookie preferences" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Necessary only" }));

    await waitFor(() =>
      expect(screen.queryByRole("region", { name: "Cookie preferences" })).not.toBeInTheDocument()
    );
    expect(document.cookie).toContain("atelier_cookie_consent");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/v1/analytics/consent"),
      expect.objectContaining({ method: "POST", credentials: "include" })
    );
  });
});
