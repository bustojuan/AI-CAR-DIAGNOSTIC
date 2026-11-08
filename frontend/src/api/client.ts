import type {
  CarApi,
  CompatibilityInput,
  Observation,
  PricesInput,
  SearchInput,
  VehiclePatch,
} from "./types";
import {
  conversationPayload,
  diagnosticPayload,
  casePayload,
  caseHistoryPayload,
  healthPayload,
  InvalidPayload,
  toolPayload,
  toolsPayload,
  vehiclePayload,
} from "./validation";

const messages: Record<string, string> = {
  database_not_configured:
    "The backend needs a PostgreSQL connection configured.",
  database_unavailable:
    "The database is unavailable. Try again when the connection is restored.",
  database_not_migrated: "The backend needs its database migrations applied.",
  missing_api_key: "The AI service is not configured on the backend.",
  llm_not_configured: "The AI service is not configured on the backend.",
  validation_error:
    "Check the fields: a value does not match the accepted format.",
  symptoms_required:
    "Describe a symptom before a new urgency assessment can be made.",
  transient_offer_not_persistable:
    "eBay offers are temporary. View them in Parts rather than saving them in a diagnosis.",
  stale_case:
    "A newer assessment exists. Refresh the case before changing its resolution.",
  invalid_resolution_transition:
    "The case status has already changed. Refresh the history.",
  case_not_assessed:
    "This conversation has no completed assessment to resolve.",
  not_found: "The requested consultation or vehicle was not found.",
  invalid_llm_output:
    "A valid report could not be obtained. Your text has been retained.",
  unsafe_llm_output:
    "The report did not pass safety validation. Your text has been retained.",
  invalid_citations:
    "The report contains invalid references and has not been displayed.",
  unsupported_vehicle:
    "This MVP supports only the Volkswagen Golf Plus 2009 2.0 TDI diesel with manual transmission.",
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly code = "network_error",
    readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function errorText(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "The operation could not be completed. Try again.";
}

export function createApi(
  base = import.meta.env.VITE_API_BASE_URL || "/api/v1",
): CarApi {
  const prefix = base.replace(/\/$/, "");
  async function request<T>(
    path: string,
    method = "GET",
    data?: unknown,
    timeout = 25000,
  ): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    try {
      const response = await fetch(prefix + path, {
        method,
        signal: controller.signal,
        credentials: "omit",
        cache: "no-store",
        headers: {
          Accept: "application/json",
          ...(data !== undefined ? { "Content-Type": "application/json" } : {}),
        },
        body: data !== undefined ? JSON.stringify(data) : undefined,
      });
      let payload: unknown;
      try {
        payload = await response.json();
      } catch {
        throw new ApiError(
          "The API returned an unexpected response.",
          "invalid_response",
        );
      }
      if (!response.ok) {
        const envelope = payload as {
          error?: { code?: string; request_id?: string };
        };
        const code = envelope?.error?.code || "server_error";
        const id =
          envelope?.error?.request_id ||
          response.headers.get("X-Request-ID") ||
          undefined;
        throw new ApiError(
          messages[code] ||
            (response.status === 503
              ? "The service is unavailable or requires backend configuration."
              : "The request could not be completed. Your information has been retained."),
          code,
          id,
        );
      }
      return payload as T;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (controller.signal.aborted)
        throw new ApiError(
          method === "GET"
            ? "The service is taking too long to respond. Check the connection again."
            : "The request timed out. The server may have saved it; review the consultation before resubmitting.",
          "timeout",
        );
      throw new ApiError(
        "Cannot connect to the backend. Check that it is running.",
      );
    } finally {
      clearTimeout(timer);
    }
  }
  const id = encodeURIComponent;
  async function validate<T>(
    promise: Promise<unknown>,
    parse: (value: unknown) => T,
  ): Promise<T> {
    try {
      return parse(await promise);
    } catch (e) {
      if (e instanceof InvalidPayload)
        throw new ApiError(
          "The API returned incomplete or inconsistent data. No report was displayed.",
          "invalid_response",
        );
      throw e;
    }
  }
  return {
    health: () => validate(request("/health"), healthPayload),
    vehicles: () =>
      validate(request("/vehicles"), (value) => {
        if (!Array.isArray(value)) throw new InvalidPayload();
        return value.map(vehiclePayload);
      }),
    tools: () => validate(request("/tools/status"), toolsPayload),
    updateVehicle: (key: string, data: VehiclePatch) =>
      validate(request(`/vehicles/${id(key)}`, "PATCH", data), vehiclePayload),
    diagnose: (vehicleId: string, data: Observation) =>
      validate(
        request(
          "/diagnostics",
          "POST",
          { ...data, vehicle_id: vehicleId },
          240000,
        ),
        diagnosticPayload,
      ),
    message: (key: string, data: Observation) =>
      validate(
        request(`/conversations/${id(key)}/messages`, "POST", data, 240000),
        diagnosticPayload,
      ),
    conversation: (key: string) =>
      validate(request(`/conversations/${id(key)}`), conversationPayload),
    diagnostic: (key: string) =>
      validate(request(`/diagnostics/${id(key)}`), diagnosticPayload),
    caseHistory: (key) =>
      validate(
        request(`/vehicles/${id(key)}/case-history`),
        caseHistoryPayload,
      ),
    resolveCase: (key, data) =>
      validate(
        request(`/conversations/${id(key)}/resolve`, "POST", data),
        casePayload,
      ),
    reopenCase: (key, data) =>
      validate(
        request(`/conversations/${id(key)}/reopen`, "POST", data),
        casePayload,
      ),
    search: (data: SearchInput) =>
      validate(request("/parts/search", "POST", data), toolPayload),
    compatibility: (data: CompatibilityInput) =>
      validate(request("/parts/compatibility", "POST", data), toolPayload),
    prices: (data: PricesInput) =>
      validate(request("/parts/prices", "POST", data), toolPayload),
  };
}
