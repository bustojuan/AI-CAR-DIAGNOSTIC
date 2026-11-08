import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, createApi } from "./client";
import { sampleReport } from "../demo/api";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});
describe("existing API contracts", () => {
  it("uses JSON POST, omits credentials and does not retry writes", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(sampleReport(crypto.randomUUID())), {
        status: 201,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    await createApi("/api/v1").diagnose("vehicle", {
      description: "Arranque difícil",
      dtcs: ["P0380"],
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/diagnostics");
    expect(JSON.parse(options.body)).toEqual({
      vehicle_id: "vehicle",
      description: "Arranque difícil",
      dtcs: ["P0380"],
    });
    expect(options.credentials).toBe("omit");
    expect(options.cache).toBe("no-store");
    expect(options.headers.Authorization).toBeUndefined();
  });
  it("uses the conversation endpoint for follow-up messages", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(sampleReport(crypto.randomUUID())), {
        status: 201,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    await createApi().message("id/with/slash", {
      description: "Más información",
    });
    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/v1/conversations/id%2Fwith%2Fslash/messages",
    );
  });
  it("localizes errors and retains the correlation ID without displaying raw secrets", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: "database_unavailable",
              message: "private-password",
              request_id: "request-7",
            },
          }),
          { status: 503 },
        ),
      ),
    );
    try {
      await createApi().health();
      throw new Error("Expected failure");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).requestId).toBe("request-7");
      expect((error as Error).message).not.toContain("private-password");
    }
  });
  it("does not silently substitute demo data when the backend is offline", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("offline"));
    vi.stubGlobal("fetch", fetchMock);
    await expect(createApi().vehicles()).rejects.toMatchObject({
      code: "network_error",
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
  it("rejects HTML proxy errors as invalid responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response("<html>proxy failure</html>", { status: 502 }),
        ),
    );
    await expect(createApi().tools()).rejects.toMatchObject({
      code: "invalid_response",
    });
  });
  it("aborts slow requests without automatically retrying", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn(
      (_url, options) =>
        new Promise((_resolve, reject) =>
          options.signal.addEventListener("abort", () =>
            reject(new DOMException("Aborted", "AbortError")),
          ),
        ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const promise = createApi().health();
    const assertion = expect(promise).rejects.toMatchObject({
      code: "timeout",
    });
    await vi.advanceTimersByTimeAsync(25001);
    await assertion;
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
