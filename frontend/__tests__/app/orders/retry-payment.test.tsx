import React from "react";
import { waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { renderWithIntl } from "../../test-utils";

const navigationState = vi.hoisted(() => ({
  searchParams: new URLSearchParams("token=return-token"),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "test-order-123" }),
  useSearchParams: () => navigationState.searchParams,
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/",
}));

vi.mock("@/lib/api", () => ({
  createStripeRetrySession: vi.fn(),
}));

import { createStripeRetrySession } from "@/lib/api";
import RetryPaymentPage from "@/app/[locale]/orders/[id]/retry-payment/page";

const mockedCreateStripeRetrySession = vi.mocked(createStripeRetrySession);

describe("RetryPaymentPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    navigationState.searchParams = new URLSearchParams("token=return-token");
    mockedCreateStripeRetrySession.mockImplementation(() => new Promise(() => {}));
  });

  it("passes the payment return token to the retry endpoint", async () => {
    renderWithIntl(<RetryPaymentPage />);

    await waitFor(() => {
      expect(mockedCreateStripeRetrySession).toHaveBeenCalledWith(
        "test-order-123",
        "return-token"
      );
    });
  });
});
