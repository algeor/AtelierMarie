import { describe, it, expect, vi, beforeEach } from "vitest";

describe("api-client handleResponse", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
    global.fetch = vi.fn();
  });

  it("dispatches session-rotated event when X-Session-Rotated header is present", async () => {
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "X-Session-Rotated": "true" }),
      json: () => Promise.resolve({ data: "ok" }),
    });

    const { get } = await import("@/lib/api-client");
    await get("/v1/test");

    expect(dispatchSpy).toHaveBeenCalledWith(expect.any(Event));
    const event = dispatchSpy.mock.calls[0]![0] as Event;
    expect(event.type).toBe("session-rotated");
  });


  it("does not dispatch when X-Session-Rotated header is absent", async () => {
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({}),
      json: () => Promise.resolve({ data: "ok" }),
    });

    const { get } = await import("@/lib/api-client");
    await get("/v1/test");

    expect(dispatchSpy).not.toHaveBeenCalled();
  });

  it("dispatches session-rotated even on error responses", async () => {
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      headers: new Headers({ "X-Session-Rotated": "true" }),
      text: () => Promise.resolve(JSON.stringify({
        error: { code: "UNAUTHORIZED", message: "Not authenticated", details: null },
      })),
    });

    const { get } = await import("@/lib/api-client");
    await expect(get("/v1/test")).rejects.toThrow();

    expect(dispatchSpy).toHaveBeenCalledWith(expect.any(Event));
    const event = dispatchSpy.mock.calls[0]![0] as Event;
    expect(event.type).toBe("session-rotated");
  });

});
