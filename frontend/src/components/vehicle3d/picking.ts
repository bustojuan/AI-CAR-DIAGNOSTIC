import type { Object3D } from "three";
import type { SceneBinding } from "./types";
import type { Box3, Vector3 } from "three";
import type { VehicleModelAsset } from "./types";

export function hoodHit(
  point: Vector3,
  bounds: Box3,
  region: VehicleModelAsset["hoodRegion"],
) {
  if (!region) return false;
  return (["x", "y", "z"] as const).every((axis, index) => {
    const extent = bounds.max[axis] - bounds.min[axis];
    const fraction = (point[axis] - bounds.min[axis]) / extent;
    return (
      extent > 0 &&
      fraction >= region.min[index] &&
      fraction <= region.max[index]
    );
  });
}

/** R3F raycasts the real geometry; bindings match explicit node ancestry only. */
export function resolveBinding(object: Object3D, bindings: SceneBinding[]) {
  let current: Object3D | null = object;
  while (current) {
    const match = bindings.find((binding) =>
      binding.meshNames.includes(current!.name),
    );
    if (match) return match;
    current = current.parent;
  }
  return null;
}
