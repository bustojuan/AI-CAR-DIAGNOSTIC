import type { EngineBayAsset, VehicleModelAsset } from "./types";
import { vehicleIllustration } from "./illustration";

// The user authorized another vehicle for the 3D illustration. Diagnostic
// applicability remains the Golf Plus; the alternative is disclosed in the UI.
export const dashboardVehicleModel: VehicleModelAsset = {
  src: "/models/golf-viii-gti.glb",
  name: "Volkswagen Golf VIII GTI",
  author: vehicleIllustration.author,
  license: vehicleIllustration.license,
  notice: "Golf VIII illustration · diagnostic vehicle: Golf Plus",
  rotation: [0, Math.PI, 0],
  fitToGeometry: true,
  poster: vehicleIllustration,
  sourceUrl: vehicleIllustration.sourceUrl,
  // This merged-material mesh has no separate hood node. Use a narrowly reviewed
  // patch of actual surface hits; no whole-car click target or hood animation.
  hoodRegion: { min: [0.19, 0.38, 0.73], max: [0.81, 0.64, 0.93] },
};

// No verified Golf Plus 2009 CFFB engine-bay GLB or mesh mapping
// is available. The Golf VIII exterior does not establish Golf Plus engine layout.
export const golfPlusEngineBay: EngineBayAsset | null = null;
