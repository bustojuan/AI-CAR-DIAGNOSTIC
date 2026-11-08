import { describe, expect, it, vi } from "vitest";
import { readHistory, safeLink, writeHistory } from "./history";

describe("local references and untrusted links", () => {
  it("stores only IDs and dates, without symptoms or personal data", () => {
    const entry = {
      conversationId: crypto.randomUUID(),
      vehicleId: crypto.randomUUID(),
      createdAt: new Date().toISOString(),
      description: "private symptom",
      vin: "private-vin",
    };
    writeHistory([entry]);
    expect(JSON.stringify(readHistory())).not.toContain("private");
    expect(localStorage.getItem("motor.conversations.v1")).not.toContain("vin");
    expect(readHistory()[0].conversationId).toBe(entry.conversationId);
  });
  it("handles corrupt or blocked browser storage", () => {
    localStorage.setItem("motor.conversations.v1", "{malformed");
    expect(readHistory()).toEqual([]);
    const spy = vi
      .spyOn(Storage.prototype, "setItem")
      .mockImplementation(() => {
        throw new DOMException("blocked");
      });
    expect(writeHistory([])).toBe(false);
    spy.mockRestore();
  });
  it.each([
    "javascript:alert(1)",
    "file:///secret",
    "https://127.0.0.1/secret",
    "https://localhost/data",
    "https://user:secret@example.com",
    "http://example.com",
  ])("rejects unsafe URL %s", (value) =>
    expect(safeLink(value)).toBeUndefined(),
  );
  it("preserves a public HTTPS attribution link", () =>
    expect(safeLink("https://example.com/reference")).toBe(
      "https://example.com/reference",
    ));
});
