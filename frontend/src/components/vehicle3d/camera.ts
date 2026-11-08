import { Box3, MathUtils, Vector3 } from "three";

export function initialView(
  bounds: Box3,
  aspect: number,
  fov: number,
  vertices?: Float32Array,
) {
  const target = bounds.getCenter(new Vector3());
  const direction = (
    vertices?.length ? new Vector3(7, 1.6, 5) : new Vector3(5, 2.5, 6)
  ).normalize();
  const right = new Vector3()
    .crossVectors(new Vector3(0, 1, 0), direction)
    .normalize();
  const up = new Vector3().crossVectors(direction, right).normalize();
  const tanV = Math.tan(MathUtils.degToRad(fov / 2));
  const tanH = tanV * Math.max(aspect, 0.1);
  let distance = 0;
  const fit = (corner: Vector3) => {
    corner.sub(target);
    distance = Math.max(
      distance,
      Math.abs(corner.dot(right)) / tanH + corner.dot(direction),
      Math.abs(corner.dot(up)) / tanV + corner.dot(direction),
    );
  };
  if (vertices?.length) {
    // Fit the entire horizontal orbit, using each vertex's actual radius/height.
    // Empty box corners would make low, rounded cars look unnecessarily small.
    const sin = Math.hypot(direction.x, direction.z);
    const cos = direction.y;
    for (let index = 0; index < vertices.length; index += 3) {
      const radius = Math.hypot(
        vertices[index] - target.x,
        vertices[index + 2] - target.z,
      );
      const height = vertices[index + 1] - target.y;
      distance = Math.max(
        distance,
        radius * Math.hypot(1 / tanH, sin) + height * cos,
        height * (sin / tanV + cos) + radius * Math.abs(sin - cos / tanV),
        height * (-sin / tanV + cos) + radius * Math.abs(sin + cos / tanV),
      );
    }
  } else
    for (const x of [bounds.min.x, bounds.max.x])
      for (const y of [bounds.min.y, bounds.max.y])
        for (const z of [bounds.min.z, bounds.max.z]) {
          fit(new Vector3(x, y, z));
        }
  const minimum = bounds.getSize(new Vector3()).length() / 2 + 0.5;
  distance = Math.max(distance * (vertices?.length ? 1.04 : 1.12), minimum);
  return {
    target,
    distance,
    minimum,
    position: direction.multiplyScalar(distance).add(target),
  };
}
