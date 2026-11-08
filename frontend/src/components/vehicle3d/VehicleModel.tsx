import { Html, useGLTF } from "@react-three/drei";
import { useEffect, useMemo, useState } from "react";
import { useThree, type ThreeEvent } from "@react-three/fiber";
import { Box3, Color, Mesh, Vector3, type Material } from "three";
import type { SceneBinding, VehicleModelAsset } from "./types";
import { hoodHit, resolveBinding } from "./picking";

export function useVehicleModel(asset: VehicleModelAsset) {
  // No remote Draco/KTX decoder defaults: deliver a locally optimized core GLB.
  // Meshopt support is supplied by Drei's bundled decoder.
  const gltf = useGLTF(asset.src, false);
  return useMemo(() => {
    const scene = gltf.scene.clone(true);
    scene.rotation.set(...(asset.rotation ?? [0, 0, 0]));
    scene.updateMatrixWorld(true);
    // Quantized / rotated meshes can have conservative accessor bounding boxes.
    // Measure actual decoded vertices once, so the car fits and rests on the floor.
    const original = new Box3().setFromObject(scene, true);
    const size = original.getSize(new Vector3());
    if (
      original.isEmpty() ||
      !Number.isFinite(size.length()) ||
      size.length() === 0
    )
      throw new Error("Empty model");
    const scale = 4.4 / Math.max(size.x, size.y, size.z);
    const center = original.getCenter(new Vector3());
    scene.traverse((object) => {
      if (object instanceof Mesh) {
        object.castShadow = true;
        object.receiveShadow = true;
      }
    });
    const position: [number, number, number] = [
      -center.x * scale,
      -original.min.y * scale,
      -center.z * scale,
    ];
    const bounds = new Box3(
      new Vector3((-size.x * scale) / 2, 0, (-size.z * scale) / 2),
      new Vector3((size.x * scale) / 2, size.y * scale, (size.z * scale) / 2),
    );
    // Cache normalized vertices once. Camera reset can then fit the actual car
    // without measuring empty box corners or scanning geometry every frame.
    let framingVertices: Float32Array | undefined;
    if (asset.fitToGeometry) {
      const meshes: Mesh[] = [];
      scene.traverse((object) => {
        if (object instanceof Mesh && object.geometry.getAttribute("position"))
          meshes.push(object);
      });
      const count = meshes.reduce(
        (sum, mesh) => sum + mesh.geometry.getAttribute("position").count,
        0,
      );
      framingVertices = new Float32Array(count * 3);
      const vertex = new Vector3();
      const offset = new Vector3(...position);
      let index = 0;
      for (const mesh of meshes) {
        const positions = mesh.geometry.getAttribute("position");
        for (let i = 0; i < positions.count; i++) {
          vertex
            .fromBufferAttribute(positions, i)
            .applyMatrix4(mesh.matrixWorld)
            .multiplyScalar(scale)
            .add(offset);
          vertex.toArray(framingVertices, index);
          index += 3;
        }
      }
    }
    return { scene, scale, position, bounds, framingVertices };
  }, [gltf.scene, asset.rotation, asset.fitToGeometry]);
}

export function VehicleModel({
  model,
  bindings = [],
  selected,
  onActivate,
  hotspots = false,
  hoodRegion,
}: {
  model: ReturnType<typeof useVehicleModel>;
  bindings?: SceneBinding[];
  selected?: string | null;
  onActivate?: (id: string) => void;
  hotspots?: boolean;
  hoodRegion?: VehicleModelAsset["hoodRegion"];
}) {
  const { gl, invalidate } = useThree();
  const [hovered, setHovered] = useState<string | null>(null);
  const anchors = useMemo(
    () =>
      bindings.flatMap((binding) => {
        const box = new Box3();
        for (const name of binding.meshNames) {
          const object = model.scene.getObjectByName(name);
          if (object) box.union(new Box3().setFromObject(object, true));
        }
        const point = box.getCenter(new Vector3());
        point.y = box.max.y + 0.02 / model.scale;
        return box.isEmpty() ? [] : [{ ...binding, point }];
      }),
    [model, bindings],
  );
  useEffect(() => {
    gl.domElement.classList.toggle("has-pick-target", !!hovered);
    return () => gl.domElement.classList.remove("has-pick-target");
  }, [gl, hovered]);
  useEffect(() => {
    const changed: {
      mesh: Mesh;
      original: Material | Material[];
      copies: Material[];
    }[] = [];
    const active = hovered || selected;
    if (!active) return;
    model.scene.traverse((object) => {
      if (
        !(object instanceof Mesh) ||
        resolveBinding(object, bindings)?.id !== active
      )
        return;
      const original = object.material;
      const copies = (Array.isArray(original) ? original : [original]).map(
        (material) => {
          const copy = material.clone();
          if ("color" in copy && copy.color instanceof Color)
            copy.color.lerp(new Color("#c9dddd"), 0.09);
          return copy;
        },
      );
      object.material = Array.isArray(original) ? copies : copies[0];
      changed.push({ mesh: object, original, copies });
    });
    invalidate();
    return () => {
      changed.forEach(({ mesh, original, copies }) => {
        mesh.material = original;
        copies.forEach((material) => material.dispose());
      });
      invalidate();
    };
  }, [model, bindings, hovered, selected, invalidate]);
  const activate = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation(); // Do not pick a component through an occluding mesh.
    const binding = resolveBinding(event.object, bindings);
    if (!onActivate || event.delta > 5) return;
    if (binding) onActivate(binding.id);
    else if (hoodHit(event.point, model.bounds, hoodRegion)) onActivate("hood");
  };
  // Cached GLTF resources are shared; R3F must not dispose them during a retry.
  return (
    <group
      scale={model.scale}
      position={model.position}
      dispose={null}
      onClick={onActivate ? activate : undefined}
      onPointerMove={
        onActivate
          ? (event) => {
              event.stopPropagation();
              setHovered(
                resolveBinding(event.object, bindings)?.id ??
                  (hoodHit(event.point, model.bounds, hoodRegion)
                    ? "hood"
                    : null),
              );
            }
          : undefined
      }
      onPointerOut={() => setHovered(null)}
    >
      <primitive object={model.scene} />
      {hotspots &&
        anchors.map((binding) => (
          <Html
            key={binding.id}
            position={binding.point.toArray()}
            center
            occlude
          >
            <button
              className={`engine-hotspot${selected === binding.id ? " is-selected" : ""}`}
              aria-label={`Inspect ${binding.label}`}
              aria-pressed={selected === binding.id}
              onClick={() => onActivate?.(binding.id)}
            >
              <span aria-hidden="true">+</span>
              <span>{binding.label}</span>
            </button>
          </Html>
        ))}
    </group>
  );
}
