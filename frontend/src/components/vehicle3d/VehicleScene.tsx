import { Suspense, useEffect, useMemo } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { Box3, PCFShadowMap, Vector3 } from "three";
import { useGLTF } from "@react-three/drei";
import { VehicleModel, useVehicleModel } from "./VehicleModel";
import { StudioLighting } from "./StudioLighting";
import { VehicleCameraControls } from "./VehicleCameraControls";
import type { SceneBinding, VehicleModelAsset, VehicleView } from "./types";

type SceneProps = {
  model: VehicleModelAsset;
  onReady: () => void;
  onFailure: () => void;
  resetVersion: number;
  visible: boolean;
  onViewChange?: (view: VehicleView) => void;
  inspection?: boolean;
  bindings?: SceneBinding[];
  selected?: string | null;
  onActivate?: (id: string) => void;
  focus?: "vehicle" | "hood";
  onFocusComplete?: (focus: "vehicle" | "hood") => void;
};

function SceneContent(props: SceneProps) {
  const { model, onReady, resetVersion, onViewChange } = props;
  const loaded = useVehicleModel(model);
  if (
    props.inspection &&
    props.bindings?.some(
      (binding) =>
        !binding.meshNames.length ||
        binding.meshNames.some((name) => !loaded.scene.getObjectByName(name)),
    )
  ) {
    throw new Error(
      "The engine-bay component mapping does not match the model",
    );
  }
  const bindings = useMemo(
    () =>
      props.bindings ||
      (props.onActivate && model.hoodMeshNames
        ? [
            {
              id: "hood",
              label: "Explore Engine Bay",
              meshNames: model.hoodMeshNames,
            },
          ]
        : []),
    [props.bindings, props.onActivate, model.hoodMeshNames],
  );
  const focusPoint = useMemo(() => {
    const box = new Box3();
    for (const name of model.hoodMeshNames || []) {
      const object = loaded.scene.getObjectByName(name);
      if (object) box.union(new Box3().setFromObject(object, true));
    }
    if (box.isEmpty()) return undefined;
    return box
      .getCenter(new Vector3())
      .multiplyScalar(loaded.scale)
      .add(new Vector3(...loaded.position));
  }, [loaded, model.hoodMeshNames]);
  const { gl, invalidate } = useThree();
  useEffect(() => {
    // Geometry and lighting stay fixed during orbit. Bake the shadow once instead
    // of rendering a 1024px shadow pass for every damping frame.
    gl.shadowMap.needsUpdate = true;
    invalidate();
    onReady();
  }, [gl, invalidate, onReady]);
  return (
    <>
      <VehicleModel
        model={loaded}
        bindings={bindings}
        selected={props.selected}
        onActivate={props.onActivate}
        hotspots={props.inspection}
        hoodRegion={props.inspection ? undefined : model.hoodRegion}
      />
      <StudioLighting />
      <VehicleCameraControls
        bounds={loaded.bounds}
        framingVertices={loaded.framingVertices}
        resetVersion={resetVersion}
        onViewChange={onViewChange}
        inspection={props.inspection}
        focus={props.focus}
        focusPoint={focusPoint}
        onFocusComplete={props.onFocusComplete}
      />
    </>
  );
}

export const clearModelCache = (src: string) => useGLTF.clear(src);

export default function VehicleScene(props: SceneProps) {
  return (
    <div className="vehicle-canvas">
      <Canvas
        frameloop={props.visible ? "demand" : "never"}
        dpr={[1, 1.5]}
        shadows={{ type: PCFShadowMap }}
        camera={{ position: [5, 2.5, 6], fov: 35, near: 0.05, far: 100 }}
        gl={{ antialias: true, alpha: true, powerPreference: "low-power" }}
        onCreated={({ gl }) => {
          gl.shadowMap.autoUpdate = false;
          gl.domElement.addEventListener(
            "webglcontextlost",
            (event) => {
              event.preventDefault();
              props.onFailure();
            },
            { once: true },
          );
        }}
      >
        <Suspense fallback={null}>
          <SceneContent {...props} />
        </Suspense>
      </Canvas>
    </div>
  );
}
