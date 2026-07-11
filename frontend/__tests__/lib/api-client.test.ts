import { vi, describe, it, expect, beforeEach } from "vitest";

// We need to test the handleResponse function's session-rotated behavior.
// Since handleResponse is not exported, we test via the public get/post methods.
// We mock global fetch.

describe("api-client X-Session-Rotated detection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it("dispatches session-rotated event when header is present", async () => {
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    const mockResponse = new Response(JSON.stringify({ data: "ok" }), {
      status: 200,
      headers: { "X-Session-Rotated": "true", "Content-Type": "application/json" },
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockResponse));

    // Dynamic import to get fresh module with mocked fetch
    const { get } = await import("@/lib/api-client");
    await get("/v1/test");

    expect(dispatchSpy).toHaveBeenCalledWith(expect.any(Event));
    const event = dispatchSpy.mock.calls[0]![0] as Event;
    expect(event.type).toBe("session-rotated");

    dispatchSpy.mockRestore();
    vi.unstubAllGlobals();
  });

  it("does not dispatch event when header is absent", async () => {
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    const mockResponse = new Response(JSON.stringify({ data: "ok" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockResponse));

    const { get } = await import("@/lib/api-client");
    await get("/v1/test");

    expect(dispatchSpy).not.toHaveBeenCalledWith(
      expect.objectContaining({ type: "session-rotated" })
    );

    dispatchSpy.mockRestore();
    vi.unstubAllGlobals();
  });

  it("dispatches event even on error responses", async () => {
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    const errorBody = { error: { code: "UNAUTHORIZED", message: "Not logged in", details: null } };
    const mockResponse = new Response(JSON.stringify(errorBody), {
      status: 401,
      headers: { "X-Session-Rotated": "true", "Content-Type": "application/json" },
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockResponse));

    const { get } = await import("@/lib/api-client");
    try {
      await get("/v1/test");
    } catch {
      // Expected to throw ApiError
    }

    expect(dispatchSpy).toHaveBeenCalledWith(
      expect.objectContaining({ type: "session-rotated" })
    );

    dispatchSpy.mockRestore();
    vi.unstubAllGlobals();
  });
});
