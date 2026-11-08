import { useEffect, useRef, type ComponentRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { Box3, MathUtils, PerspectiveCamera, TOUCH, Vector3 } from "three";
import { initialView } from "./camera";
import type { VehicleView } from "./types";

export function VehicleCameraControls({
  bounds,
  framingVertices,
  resetVersion,
  onViewChange,
  inspection = false,
  focus = "vehicle",
  focusPoint,
  onFocusComplete,
}: {
  bounds: Box3;
  framingVertices?: Float32Array;
  resetVersion: number;
  onViewChange?: (view: VehicleView) => void;
  inspection?: boolean;
  focus?: "vehicle" | "hood";
  focusPoint?: Vector3;
  onFocusComplete?: (focus: "vehicle" | "hood") => void;
}) {
  const controls = useRef<ComponentRef<typeof OrbitControls>>(null);
  const { camera, gl, invalidate } = useThree();
  const lastFocus = useRef(focus);
  const saved = useRef<{ position: Vector3; target: Vector3 } | null>(null);
  const animation = useRef<{
    elapsed: number;
    duration: number;
    fromPosition: Vector3;
    fromTarget: Vector3;
    position: Vector3;
    target: Vector3;
    focus: "vehicle" | "hood";
  } | null>(null);
  const completion = useRef(onFocusComplete);
  completion.current = onFocusComplete;
  useFrame((_, delta) => {
    const orbit = controls.current;
    const transition = animation.current;
    if (orbit && transition) {
      // Demand rendering resumes after an idle period. Its first delta can be
      // several seconds; cap it so the first frame cannot skip the transition.
      transition.elapsed += Math.min(delta, 0.05);
      const t = Math.min(1, transition.elapsed / transition.duration);
      const eased = t * t * (3 - 2 * t);
      camera.position.lerpVectors(
        transition.fromPosition,
        transition.position,
        eased,
      );
      orbit.target.lerpVectors(transition.fromTarget, transition.target, eased);
      orbit.update();
      invalidate();
      if (t === 1) {
        animation.current = null;
        orbit.enabled = transition.focus === "vehicle";
        orbit.enableDamping = true;
        completion.current?.(transition.focus);
      }
    }
    if (controls.current)
      controls.current.dampingFactor =
        1 - Math.pow(0.91, Math.min(delta, 0.1) * 60);
  }, -2);
  useEffect(() => {
    if (lastFocus.current === focus) return;
    const orbit = controls.current;
    if (!orbit) return;
    lastFocus.current = focus;
    orbit.enableDamping = false;
    orbit.update();
    let destination = saved.current;
    if (focus === "hood") {
      if (!focusPoint) {
        orbit.enableDamping = true;
        completion.current?.(focus);
        return;
      }
      saved.current = {
        position: camera.position.clone(),
        target: orbit.target.clone(),
      };
      const center = bounds.getCenter(new Vector3());
      const direction = camera.position.clone().sub(center);
      const minimum = bounds.getSize(new Vector3()).length() / 2 + 0.5;
      destination = {
        position: direction
          .setLength(Math.max(direction.length() * 0.88, minimum * 1.4))
          .add(center),
        target: focusPoint.clone(),
      };
    }
    if (!destination) {
      orbit.enableDamping = true;
      orbit.enabled = true;
      completion.current?.(focus);
      return;
    }
    orbit.enabled = false;
    animation.current = {
      elapsed: 0,
      duration: window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
        ? 0.001
        : 0.65,
      fromPosition: camera.position.clone(),
      fromTarget: orbit.target.clone(),
      ...destination,
      focus,
    };
    invalidate();
  }, [focus, focusPoint, bounds, camera, invalidate]);
  // Deliberately excludes resize: changing viewport must retain the selected angle.
  useEffect(() => {
    const orbit = controls.current;
    if (!orbit || !(camera instanceof PerspectiveCamera)) return;
    const initial = initialView(
      bounds,
      camera.aspect,
      camera.fov,
      framingVertices,
    );
    orbit.enableDamping = false;
    orbit.update(); // Flush any residual damping before setting the initial pose.
    camera.position.copy(initial.position);
    camera.near = 0.05;
    camera.far = 100;
    camera.updateProjectionMatrix();
    orbit.target.copy(initial.target);
    orbit.minDistance = initial.minimum;
    orbit.maxDistance = initial.distance * 1.25;
    orbit.update();
    orbit.saveState();
    orbit.enableDamping = true;
    invalidate();
  }, [bounds, framingVertices, camera, resetVersion, invalidate]);

  useEffect(() => {
    const canvas = gl.domElement;
    canvas.tabIndex = 0;
    canvas.setAttribute(
      "aria-label",
      inspection
        ? "Explore engine bay: drag or use arrow keys to rotate; scroll or pinch to zoom"
        : "Explore 3D vehicle: drag or use arrow keys to rotate",
    );
    // The browser may scroll vertically; a horizontal gesture belongs to the car.
    // Pointer cancellation lets OrbitControls release capture on native scrolling.
    canvas.style.touchAction = inspection ? "none" : "pan-y";
    const keyboard = (event: KeyboardEvent) => {
      const orbit = controls.current;
      if (
        !orbit ||
        !orbit.enabled ||
        !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)
      )
        return;
      event.preventDefault();
      if (event.key === "ArrowLeft" || event.key === "ArrowRight")
        orbit.setAzimuthalAngle(
          orbit.getAzimuthalAngle() +
            (event.key === "ArrowLeft" ? -1 : 1) * 0.15,
        );
      else
        orbit.setPolarAngle(
          MathUtils.clamp(
            orbit.getPolarAngle() + (event.key === "ArrowUp" ? -1 : 1) * 0.08,
            orbit.minPolarAngle,
            orbit.maxPolarAngle,
          ),
        );
      invalidate();
    };
    canvas.addEventListener("keydown", keyboard);
    return () => canvas.removeEventListener("keydown", keyboard);
  }, [gl, invalidate, inspection]);
  return (
    <OrbitControls
      ref={controls}
      domElement={gl.domElement}
      makeDefault
      enablePan={false}
      enableZoom={inspection}
      enableDamping
      dampingFactor={0.09}
      rotateSpeed={0.65}
      autoRotate={false}
      minPolarAngle={inspection ? Math.PI / 6 : Math.PI / 4}
      maxPolarAngle={Math.PI / 2 - 0.08}
      touches={{ ONE: TOUCH.ROTATE, TWO: TOUCH.DOLLY_ROTATE }}
      onChange={() => {
        const orbit = controls.current;
        if (orbit && onViewChange)
          onViewChange({
            azimuth: orbit.getAzimuthalAngle(),
            polar: orbit.getPolarAngle(),
            distance: orbit.getDistance(),
          });
      }}
    />
  );
}
