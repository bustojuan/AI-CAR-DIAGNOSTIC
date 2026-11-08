export type VehicleModelAsset = {
  /** Local authorized GLB/glTF, with its textures/buffers served locally too. */
  src: string;
  name: string;
  author: string;
  license: string;
  /** Human-readable distinction between the visual model and diagnostic vehicle. */
  notice?: string;
  /** Attribution/provenance link for the locally served asset. */
  sourceUrl?: string;
  /** Export with +Y up and the nose toward +Z, or correct orientation here. */
  rotation?: [number, number, number];
  /** Match the visible mesh silhouette instead of empty bounding-box corners. */
  fitToGeometry?: boolean;
  /** A render of this same vehicle for loading and WebGL failures. */
  poster?: { src: string; alt: string };
  /** Verified mesh names on this particular exterior asset; never inferred from positions. */
  hoodMeshNames?: string[];
  /** Reviewed hood patch as fractions of the rendered model bounds; uses real mesh ray hits. */
  hoodRegion?: { min: [number, number, number]; max: [number, number, number] };
};

export type VehicleView = { azimuth: number; polar: number; distance: number };

export type VehicleIdentity = {
  manufacturer: string;
  model: string;
  model_year: number;
  engine: string;
  engine_code?: string | null;
};
export type ComponentId =
  | "battery"
  | "engine"
  | "coolant"
  | "air-filter"
  | "engine-cover"
  | "brake-fluid";
export type SceneBinding = { id: string; label: string; meshNames: string[] };
export type TechnicalEvidence = {
  title: string;
  url: string;
  publisher: string;
};
export type EngineBayAsset = {
  model: VehicleModelAsset;
  vehicle: VehicleIdentity & { engine_code: string };
  verified: boolean;
  verifiedBy: string;
  components: {
    id: ComponentId;
    meshNames: string[];
    evidence: TechnicalEvidence[];
  }[];
};
export type EngineBayPhoto = {
  title: string;
  src: string;
  width: number;
  height: number;
  alt: string;
  depictedVehicle: string;
  author: string;
  sourceUrl: string;
  license: string;
  licenseUrl: string;
  notice: string;
  hotspots: { id: ComponentId; x: number; y: number; review: string }[];
};
export type EngineExplorerOptions = {
  vehicle: VehicleIdentity;
  engineBay: EngineBayAsset | null;
  photo?: EngineBayPhoto | null;
  onAskAI?: (draft: string) => void;
  onFindParts?: (component: string) => void;
  onInspectionViewChange?: (view: VehicleView) => void;
};
