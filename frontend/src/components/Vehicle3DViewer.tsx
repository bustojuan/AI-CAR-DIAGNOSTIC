import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Rotate3D, RotateCcw, ScanLine } from "lucide-react";
import { CarIllustration, Spinner } from "./ui";
import { EngineBayInspector } from "./vehicle3d/EngineBayInspector";
import { ViewerBoundary } from "./vehicle3d/ViewerBoundary";
import { AssetCredits } from "./vehicle3d/AssetCredits";
import type {
  EngineExplorerOptions,
  VehicleModelAsset,
  VehicleView,
} from "./vehicle3d/types";
import "./vehicle3d/viewer.css";

type ViewerProps = {
  model: VehicleModelAsset | null;
  onViewChange?: (view: VehicleView) => void;
  explorer?: EngineExplorerOptions;
};

function StaticVehicle({
  caption,
  hidden = false,
  poster,
}: {
  caption: string;
  hidden?: boolean;
  poster?: VehicleModelAsset["poster"];
}) {
  return (
    <div
      className={`vehicle-static ${hidden ? "is-hidden" : ""}`}
      aria-hidden={hidden || undefined}
    >
      <CarIllustration src={poster?.src} alt={poster?.alt} />
      {!hidden && <span className="viewer-caption">{caption}</span>}
    </div>
  );
}

function ViewerInstance({ model, onViewChange, explorer }: ViewerProps) {
  const [phase, setPhase] = useState<
    "loading" | "ready" | "failed" | "missing"
  >(model ? "loading" : "missing");
  const [mode, setMode] = useState<
    "vehicle" | "entering" | "engine" | "leaving"
  >("vehicle");
  const [attempt, setAttempt] = useState(0);
  const [resetVersion, setResetVersion] = useState(0);
  const [visible, setVisible] = useState(true);
  // The initial app bundle does not load Three/Fiber/Drei. No model means no canvas.
  const Scene = useMemo(
    () =>
      lazy(() =>
        import("./vehicle3d/VehicleScene").then((module) => {
          if (attempt > 0 && model) module.clearModelCache(model.src);
          return module;
        }),
      ),
    [attempt, model?.src],
  );
  const root = useRef<HTMLDivElement>(null);
  const ready = useCallback(() => setPhase("ready"), []);
  const fail = useCallback(() => {
    setPhase("failed");
    setMode((value) => (value === "entering" ? "engine" : value));
  }, []);
  const requestInspection = useCallback(() => {
    if (!explorer || mode !== "vehicle") return;
    setMode(
      phase === "ready" && model?.hoodMeshNames?.length ? "entering" : "engine",
    );
  }, [explorer, mode, phase, model]);
  const activate = useCallback(
    (id: string) => {
      if (id === "hood") requestInspection();
    },
    [requestInspection],
  );
  const focused = useCallback((focus: "vehicle" | "hood") => {
    setMode((value) =>
      focus === "hood" && value === "entering"
        ? "engine"
        : focus === "vehicle" && value === "leaving"
          ? "vehicle"
          : value,
    );
  }, []);
  const close = useCallback(() => {
    setMode(
      phase === "ready" && model?.hoodMeshNames?.length ? "leaving" : "vehicle",
    );
  }, [phase, model]);
  useEffect(() => {
    const observer =
      typeof IntersectionObserver === "undefined"
        ? null
        : new IntersectionObserver((entries) =>
            setVisible(entries[0]?.isIntersecting ?? false),
          );
    if (root.current) observer?.observe(root.current);
    return () => observer?.disconnect();
  }, []);
  useEffect(() => {
    if (phase !== "loading") return;
    const timer = window.setTimeout(fail, 30000);
    return () => window.clearTimeout(timer);
  }, [phase, attempt, fail]);
  return (
    <div
      className={`vehicle-viewer phase-${phase}`}
      ref={root}
      lang="en"
      aria-label={
        model ? `3D view of ${model.name}` : "Static vehicle illustration"
      }
    >
      <StaticVehicle
        poster={model?.poster}
        hidden={phase === "ready"}
        caption={
          phase === "failed"
            ? "Static image · 3D viewer could not be loaded"
            : phase === "missing"
              ? "Static image · 3D model unavailable"
              : "Preparing 3D view…"
        }
      />
      {model && phase !== "failed" && (
        <ViewerBoundary key={attempt} onFailure={fail}>
          <Suspense fallback={null}>
            <Scene
              model={model}
              onReady={ready}
              onFailure={fail}
              resetVersion={resetVersion}
              visible={visible && mode !== "engine"}
              onViewChange={onViewChange}
              onActivate={explorer ? activate : undefined}
              focus={
                mode === "entering" || mode === "engine" ? "hood" : "vehicle"
              }
              onFocusComplete={focused}
            />
          </Suspense>
        </ViewerBoundary>
      )}
      {phase === "loading" && (
        <div className="viewer-loading">
          <Spinner label="Loading 3D model…" />
        </div>
      )}
      {phase === "failed" && (
        <button
          className="viewer-retry"
          onClick={() => {
            setPhase("loading");
            setAttempt((value) => value + 1);
          }}
        >
          Retry 3D view
        </button>
      )}
      <div className="viewer-asset-credits">
        <AssetCredits model={model || undefined} />
      </div>
      {explorer && (
        <button
          className="viewer-explore"
          onClick={requestInspection}
          disabled={mode !== "vehicle"}
          aria-haspopup="dialog"
          aria-expanded={mode === "engine"}
        >
          <ScanLine size={15} aria-hidden="true" />
          {mode === "entering" ? "Moving to inspection…" : "Explore Engine Bay"}
        </button>
      )}
      {phase === "ready" && (
        <div className="viewer-toolbar">
          <span>
            <Rotate3D size={17} aria-hidden="true" />
            Drag to explore the vehicle in 360°
          </span>
          <button
            onClick={() => setResetVersion((value) => value + 1)}
            disabled={mode !== "vehicle"}
            aria-label="Reset vehicle view"
            title="Reset view"
          >
            <RotateCcw size={16} aria-hidden="true" />
          </button>
        </div>
      )}
      {phase === "ready" && (
        <span className="sr-only" role="status">
          3D model loaded. Drag or use arrow keys to rotate.
          {explorer
            ? model?.hoodMeshNames?.length || model?.hoodRegion
              ? " Select the hood or Explore Engine Bay to inspect."
              : " Select Explore Engine Bay to inspect."
            : ""}
        </span>
      )}
      {phase === "failed" && (
        <span className="sr-only" role="status">
          The 3D viewer is unavailable. A static image is shown.
        </span>
      )}
      {mode === "engine" && explorer && (
        <EngineBayInspector
          options={explorer}
          exteriorName={model?.name || "a static illustration"}
          onClose={close}
        />
      )}
    </div>
  );
}

export function Vehicle3DViewer(props: ViewerProps) {
  return <ViewerInstance key={props.model?.src || "missing"} {...props} />;
}
