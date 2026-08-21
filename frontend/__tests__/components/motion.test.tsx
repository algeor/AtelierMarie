import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CountUpMetric, ScrollReveal } from "@/components/motion";

const originalIntersectionObserver = globalThis.IntersectionObserver;
const originalRequestAnimationFrame = globalThis.requestAnimationFrame;
const originalCancelAnimationFrame = globalThis.cancelAnimationFrame;
const originalMatchMedia = window.matchMedia;

function mockMatchMedia(matches: boolean) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}

function mockIntersectionObserver() {
  const instances: Array<{
    callback: IntersectionObserverCallback;
    disconnect: ReturnType<typeof vi.fn>;
  }> = [];

  class IntersectionObserverMock {
    readonly root = null;
    readonly rootMargin = "";
    readonly thresholds = [];
    disconnect = vi.fn();
    observe = vi.fn();
    takeRecords = vi.fn(() => []);
    unobserve = vi.fn();

    constructor(callback: IntersectionObserverCallback) {
      instances.push({ callback, disconnect: this.disconnect });
    }
  }

  globalThis.IntersectionObserver = IntersectionObserverMock as unknown as typeof IntersectionObserver;
  return instances;
}

afterEach(() => {
  globalThis.IntersectionObserver = originalIntersectionObserver;
  globalThis.requestAnimationFrame = originalRequestAnimationFrame;
  globalThis.cancelAnimationFrame = originalCancelAnimationFrame;
  window.matchMedia = originalMatchMedia;
  vi.restoreAllMocks();
});

describe("motion primitives", () => {
  it("reveals content after it intersects", async () => {
    mockMatchMedia(false);
    const observers = mockIntersectionObserver();

    render(<ScrollReveal>Fresh card</ScrollReveal>);

    const card = screen.getByText("Fresh card").closest("[data-visible]");
    expect(card).toHaveAttribute("data-visible", "false");

    await waitFor(() => expect(observers).toHaveLength(1));
    const observer = observers[0]!;
    act(() => {
      observer.callback([{ isIntersecting: true } as IntersectionObserverEntry], {} as IntersectionObserver);
    });

    expect(card).toHaveAttribute("data-visible", "true");
    expect(observer.disconnect).toHaveBeenCalled();
  });

  it("renders reveal content visible without IntersectionObserver", async () => {
    mockMatchMedia(false);
    globalThis.IntersectionObserver = undefined as unknown as typeof IntersectionObserver;

    render(<ScrollReveal>Fallback card</ScrollReveal>);

    await waitFor(() => {
      expect(screen.getByText("Fallback card").closest("[data-visible]")).toHaveAttribute("data-visible", "true");
    });
  });

  it("renders reveal content visible for reduced motion", async () => {
    mockMatchMedia(true);
    mockIntersectionObserver();

    render(<ScrollReveal>Quiet card</ScrollReveal>);

    await waitFor(() => {
      expect(screen.getByText("Quiet card").closest("[data-visible]")).toHaveAttribute("data-visible", "true");
    });
  });

  it("counts numeric values to the final formatted value", async () => {
    mockMatchMedia(false);
    const observers = mockIntersectionObserver();
    globalThis.requestAnimationFrame = vi.fn((callback: FrameRequestCallback) => {
      callback(performance.now() + 1000);
      return 1;
    });
    globalThis.cancelAnimationFrame = vi.fn();

    render(<CountUpMetric value="€42.00" countTo={4200} formatter={(value) => `€${(value / 100).toFixed(2)}`} />);

    await waitFor(() => expect(observers).toHaveLength(1));
    const observer = observers[0]!;
    act(() => {
      observer.callback([{ isIntersecting: true } as IntersectionObserverEntry], {} as IntersectionObserver);
    });

    expect(await screen.findByText("€42.00")).toBeInTheDocument();
  });

  it("keeps non-numeric metric text static", () => {
    mockMatchMedia(false);
    mockIntersectionObserver();

    render(<CountUpMetric value="healthy" />);

    expect(screen.getByText("healthy")).toBeInTheDocument();
  });
});
