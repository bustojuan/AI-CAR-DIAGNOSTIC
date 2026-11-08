import type { HistoryEntry } from "../api/types";

const KEY = "motor.conversations.v1";
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function readHistory(): HistoryEntry[] {
  try {
    const raw: unknown = JSON.parse(localStorage.getItem(KEY) || "[]");
    if (!Array.isArray(raw)) return [];
    return raw
      .filter(
        (item): item is HistoryEntry =>
          item &&
          uuid.test(item.conversationId) &&
          uuid.test(item.vehicleId) &&
          typeof item.createdAt === "string" &&
          Number.isFinite(Date.parse(item.createdAt)),
      )
      .slice(0, 50);
  } catch {
    return [];
  }
}
export function writeHistory(entries: HistoryEntry[]): boolean {
  try {
    // No symptoms, full messages, vehicle notes or VIN are stored in the browser.
    localStorage.setItem(
      KEY,
      JSON.stringify(
        entries
          .slice(0, 50)
          .map(({ conversationId, vehicleId, createdAt }) => ({
            conversationId,
            vehicleId,
            createdAt,
          })),
      ),
    );
    return true;
  } catch {
    return false;
  }
}
export function safeLink(value?: string | null): string | undefined {
  if (!value) return;
  try {
    const url = new URL(value);
    const host = url.hostname.toLowerCase().replace(/\.$/, "");
    if (
      url.protocol !== "https:" ||
      url.username ||
      url.password ||
      !host.includes(".") ||
      host.endsWith(".local") ||
      host.endsWith(".localhost") ||
      host === "localhost" ||
      /^\d+\.\d+\.\d+\.\d+$/.test(host) ||
      host.includes(":")
    )
      return;
    return url.href;
  } catch {
    return;
  }
}
export function dateLabel(value: string, includeYear = false): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Date unavailable"
    : new Intl.DateTimeFormat("en-GB", {
        day: "numeric",
        month: "short",
        year: includeYear ? "numeric" : undefined,
        hour: "2-digit",
        minute: "2-digit",
      }).format(date);
}
