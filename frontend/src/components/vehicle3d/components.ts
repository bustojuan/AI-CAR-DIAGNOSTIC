import type { ComponentId, EngineBayAsset, VehicleIdentity } from "./types";

export const componentTopics: Record<
  ComponentId,
  {
    name: string;
    function: string;
    symptoms: string[];
    partsQuery: string;
  }
> = {
  battery: {
    name: "Battery",
    function:
      "Stores electrical energy and supplies the starter and electrical systems.",
    symptoms: [
      "Slow cranking or a failure to crank",
      "Dim lights or electrical resets",
    ],
    partsQuery: "battery",
  },
  engine: {
    name: "Engine assembly",
    function:
      "Converts fuel energy into mechanical power to drive the vehicle.",
    symptoms: [
      "Rough running or unusual vibration",
      "Loss of power or unusual noise",
    ],
    partsQuery: "engine assembly",
  },
  coolant: {
    name: "Coolant expansion tank",
    function:
      "Provides a coolant reservoir and accommodates changes in coolant volume as temperature changes.",
    symptoms: [
      "Repeated coolant loss",
      "High coolant temperature or a coolant warning",
    ],
    partsQuery: "coolant expansion tank",
  },
  "air-filter": {
    name: "Air filter housing",
    function:
      "Holds the air filter and routes filtered air toward the engine intake.",
    symptoms: [
      "Reduced performance where intake airflow is restricted",
      "Intake noise or a damaged housing",
    ],
    partsQuery: "air filter housing",
  },
  "engine-cover": {
    name: "Engine cover",
    function:
      "Covers the top of the engine and may reduce noise and shield components. It is not the engine assembly itself.",
    symptoms: [
      "Rattling from loose cover mountings",
      "A visibly damaged or displaced cover",
    ],
    partsQuery: "engine cover",
  },
  "brake-fluid": {
    name: "Brake fluid reservoir",
    function:
      "Stores fluid for the hydraulic brake system. Its location and specifications must be verified for the actual vehicle.",
    symptoms: [
      "Brake fluid level warning",
      "Reported fluid loss or impaired braking requires professional assessment",
    ],
    partsQuery: "brake fluid reservoir",
  },
};

export function engineBayAvailability(
  asset: EngineBayAsset | null,
  vehicle: VehicleIdentity,
) {
  if (!asset)
    return `A verified engine-bay model for ${vehicle.manufacturer} ${vehicle.model} ${vehicle.model_year} ${vehicle.engine} has not been supplied.`;
  if (!asset.verified || !asset.verifiedBy.trim())
    return "This engine-bay asset has not been verified.";
  const normalize = (value: string) => value.trim().toLowerCase();
  if (
    ["manufacturer", "model", "engine"].some((key) => {
      const field = key as "manufacturer" | "model" | "engine";
      return normalize(asset.vehicle[field]) !== normalize(vehicle[field]);
    }) ||
    asset.vehicle.model_year !== vehicle.model_year
  )
    return "This engine-bay asset does not match the diagnostic vehicle.";
  if (!vehicle.engine_code || !asset.vehicle.engine_code.trim())
    return "The engine code must be confirmed before this engine-bay model can be used.";
  if (normalize(vehicle.engine_code) !== normalize(asset.vehicle.engine_code))
    return "This engine-bay asset does not match the confirmed engine code.";
  return null;
}

export function componentDraft(id: ComponentId, vehicle: VehicleIdentity) {
  return `I would like to ask about the ${componentTopics[id].name.toLowerCase()} on my ${vehicle.manufacturer} ${vehicle.model} ${vehicle.model_year} ${vehicle.engine}. No component fault has been confirmed. My observed symptoms are: `;
}
