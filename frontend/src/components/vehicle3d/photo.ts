import type { EngineBayPhoto } from "./types";

// Photo and the derived location annotations: CC BY-NC-SA 2.0, credit VW TDI.
// Original creator's photograph, not an extracted workshop-manual illustration.
// The licensed original is served locally, unmodified. See docs/ENGINE_BAY_PHOTO.md.
export const engineBayPhoto: EngineBayPhoto = {
  title: "under hood - overview",
  src: "/images/golf-2006-tdi-bew-engine-bay.jpg",
  width: 2560,
  height: 1920,
  alt: "Complete engine compartment of a 2006 Volkswagen Golf 1.9 TDI BEW, viewed from the front with the hood raised and decorative engine cover removed",
  depictedVehicle:
    "Reference photo: Volkswagen Golf 2006 · 1.9 TDI BEW · Not Golf Plus 2.0 TDI",
  author: "VW TDI",
  sourceUrl: "https://www.flickr.com/photos/vw_tdi/192839547/",
  license: "CC BY-NC-SA 2.0 · Non-commercial",
  licenseUrl: "https://creativecommons.org/licenses/by-nc-sa/2.0/",
  notice:
    "Illustrative engine bay — component layout may differ from your vehicle.",
  hotspots: [
    {
      id: "engine",
      x: 0.43,
      y: 0.51,
      review:
        "Visible engine assembly at the center of the creator's overview; no decorative engine cover is fitted.",
    },
    {
      id: "coolant",
      x: 0.113,
      y: 0.474,
      review:
        "Translucent tank at image left, visually cross-checked against the same photographer's captioned coolant expansion tank close-up (192835943).",
    },
    {
      id: "air-filter",
      x: 0.847,
      y: 0.467,
      review:
        "Large airbox connected to the intake hose at image right, cross-checked against the photographer's captioned airbox close-up (192839546).",
    },
  ],
};
