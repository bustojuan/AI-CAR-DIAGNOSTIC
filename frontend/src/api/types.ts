import type { components } from "./schema";

export type Vehicle = components["schemas"]["Vehicle"] & { vehicle_id: string };
export type VehiclePatch = components["schemas"]["VehiclePatch"];
export type Diagnostic = components["schemas"]["Diagnostic"] & {
  diagnostic_id: string;
  created_at: string;
};
export type Observation = components["schemas"]["MessageRequest"];
export type Conversation = components["schemas"]["Conversation"] & {
  conversation_id: string;
  created_at: string;
};
export type ToolResult = components["schemas"]["AutomotiveResult"];
export type Part = components["schemas"]["Part"];
export type Price = components["schemas"]["Price"];
export type ToolsStatus = components["schemas"]["ToolResult"];
export type Health = {
  status: "ok" | "degraded";
  persistence: string;
  llm_configured: boolean;
  rag_available: boolean;
  mcp_available: boolean;
};
export type SearchInput = components["schemas"]["PartsSearchRequest"];
export type CompatibilityInput = components["schemas"]["CompatibilityRequest"];
export type PricesInput = components["schemas"]["GetPartPrices"];
export type CaseSummary = components["schemas"]["CaseSummary"];
export type VehicleUrgency = components["schemas"]["VehicleUrgency"];
export type CaseHistory = components["schemas"]["CaseHistory"];
export type ResolveCaseRequest = components["schemas"]["ResolveCaseRequest"];
export type CaseVersion = components["schemas"]["CaseVersion"];
export type HistoryEntry = {
  conversationId: string;
  vehicleId: string;
  createdAt: string;
};

export interface CarApi {
  health(): Promise<Health>;
  vehicles(): Promise<Vehicle[]>;
  tools(): Promise<ToolsStatus>;
  updateVehicle(id: string, data: VehiclePatch): Promise<Vehicle>;
  diagnose(vehicleId: string, observation: Observation): Promise<Diagnostic>;
  message(
    conversationId: string,
    observation: Observation,
  ): Promise<Diagnostic>;
  conversation(id: string): Promise<Conversation>;
  diagnostic(id: string): Promise<Diagnostic>;
  caseHistory(vehicleId: string): Promise<CaseHistory>;
  resolveCase(id: string, data: ResolveCaseRequest): Promise<CaseSummary>;
  reopenCase(id: string, data: CaseVersion): Promise<CaseSummary>;
  search(data: SearchInput): Promise<ToolResult>;
  compatibility(data: CompatibilityInput): Promise<ToolResult>;
  prices(data: PricesInput): Promise<ToolResult>;
}
