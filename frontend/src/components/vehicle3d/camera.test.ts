import { expect, it } from "vitest";
import { Box3, PerspectiveCamera, Vector3 } from "three";
import { initialView } from "./camera";

it.each([0.7, 1.5, 2.5])(
  "fits all model bounds outside the body at aspect %s",
  (aspect) => {
    const bounds = new Box3(new Vector3(-1, 0, -2.2), new Vector3(1, 1.8, 2.2));
    const initial = initialView(bounds, aspect, 35);
    const camera = new PerspectiveCamera(35, aspect, 0.05, 100);
    camera.position.copy(initial.position);
    camera.lookAt(initial.target);
    camera.updateMatrixWorld();
    expect(initial.distance).toBeGreaterThanOrEqual(initial.minimum);
    expect(bounds.containsPoint(camera.position)).toBe(false);
    for (const x of [-1, 1])
      for (const y of [0, 1.8])
        for (const z of [-2.2, 2.2]) {
          const point = new Vector3(x, y, z).project(camera);
          expect(Math.abs(point.x)).toBeLessThan(1);
          expect(Math.abs(point.y)).toBeLessThan(1);
          expect(Math.abs(point.z)).toBeLessThan(1);
        }
  },
);

it.each([0.7, 1.5, 2.5])(
  "fits a rounded mesh through a full horizontal orbit at aspect %s",
  (aspect) => {
    // Elliptical rings approximate a rounded hatchback, including its roof profile.
    const points: number[] = [];
    for (const [height, radius] of [
      [0, 1],
      [0.7, 1],
      [1.5, 0.65],
    ])
      for (let i = 0; i < 40; i++) {
        const angle = (i / 40) * Math.PI * 2;
        points.push(
          Math.cos(angle) * radius,
          height,
          Math.sin(angle) * 2.2 * radius,
        );
      }
    const bounds = new Box3(new Vector3(-1, 0, -2.2), new Vector3(1, 1.5, 2.2));
    const initial = initialView(bounds, aspect, 35, new Float32Array(points));
    expect(initial.distance).toBeLessThan(
      initialView(bounds, aspect, 35).distance,
    );
    const camera = new PerspectiveCamera(35, aspect, 0.05, 100);
    const direction = initial.position.clone().sub(initial.target);
    for (let turn = 0; turn < 16; turn++) {
      camera.position.copy(
        direction
          .clone()
          .applyAxisAngle(new Vector3(0, 1, 0), (turn * Math.PI) / 8)
          .add(initial.target),
      );
      camera.lookAt(initial.target);
      camera.updateMatrixWorld();
      expect(bounds.containsPoint(camera.position)).toBe(false);
      for (let i = 0; i < points.length; i += 3) {
        const point = new Vector3().fromArray(points, i).project(camera);
        expect(Math.abs(point.x)).toBeLessThan(1);
        expect(Math.abs(point.y)).toBeLessThan(1);
      }
    }
  },
);
