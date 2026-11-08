import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";
import { ArrowLeft, Box, RotateCcw } from "lucide-react";
import { Spinner } from "../ui";
import { ComponentInfoPanel } from "./ComponentInfoPanel";
import { componentTopics, engineBayAvailability } from "./components";
import { ViewerBoundary } from "./ViewerBoundary";
import { EngineBayPhotoViewer } from "./EngineBayPhotoViewer";
import { engineBayPhoto } from "./photo";
import type {
  ComponentId,
  EngineBayAsset,
  EngineExplorerOptions,
} from "./types";
import "./engine-bay.css";

function EngineBayViewport({
  asset,
  selected,
  onSelect,
  onMapped,
  onViewChange,
}: {
  asset: EngineBayAsset;
  selected: ComponentId | null;
  onSelect: (id: ComponentId) => void;
  onMapped: (ids: ComponentId[]) => void;
  onViewChange?: EngineExplorerOptions["onInspectionViewChange"];
}) {
  const [phase, setPhase] = useState("loading");
  const [attempt, setAttempt] = useState(0);
  const [resetVersion, setResetVersion] = useState(0);
  const Scene = useMemo(
    () =>
      lazy(() =>
        import("./VehicleScene").then((module) => {
          if (attempt) module.clearModelCache(asset.model.src);
          return module;
        }),
      ),
    [attempt, asset.model.src],
  );
  const ready = useCallback(() => {
    setPhase("ready");
    onMapped(asset.components.map((component) => component.id));
  }, [asset, onMapped]);
  const fail = useCallback(() => {
    setPhase("failed");
    onMapped([]);
  }, [onMapped]);
  const bindings = useMemo(
    () =>
      asset.components.map((component) => ({
        id: component.id,
        label: componentTopics[component.id].name,
        meshNames: component.meshNames,
      })),
    [asset],
  );
  const activate = useCallback(
    (id: string) => {
      if (Object.hasOwn(componentTopics, id)) onSelect(id as ComponentId);
    },
    [onSelect],
  );
  useEffect(() => {
    if (phase !== "loading") return;
    const timer = window.setTimeout(fail, 30000);
    return () => window.clearTimeout(timer);
  }, [phase, attempt, fail]);
  return (
    <div className="engine-scene" aria-label="Engine bay 3D inspection">
      {phase !== "failed" && (
        <ViewerBoundary key={attempt} onFailure={fail}>
          <Suspense fallback={null}>
            <Scene
              model={asset.model}
              onReady={ready}
              onFailure={fail}
              resetVersion={resetVersion}
              visible
              inspection
              bindings={bindings}
              selected={selected}
              onActivate={activate}
              onViewChange={onViewChange}
            />
          </Suspense>
        </ViewerBoundary>
      )}
      {phase === "loading" && (
        <div className="engine-scene-status">
          <Spinner label="Loading engine bay…" />
        </div>
      )}
      {phase === "failed" && (
        <div className="engine-scene-status" role="status">
          <h3>The inspection model could not be loaded</h3>
          <p>The component topics remain available.</p>
          <button
            className="button secondary"
            onClick={() => {
              setPhase("loading");
              setAttempt((value) => value + 1);
            }}
          >
            Retry engine bay
          </button>
        </div>
      )}
      {phase === "ready" && (
        <div className="engine-scene-toolbar">
          <span>
            Drag to rotate · scroll or pinch to zoom · select a component
          </span>
          <button
            aria-label="Reset engine bay view"
            onClick={() => setResetVersion((value) => value + 1)}
          >
            <RotateCcw size={17} />
          </button>
        </div>
      )}
    </div>
  );
}

export function EngineBayInspector({
  options,
  exteriorName,
  onClose,
}: {
  options: EngineExplorerOptions;
  exteriorName: string;
  onClose: () => void;
}) {
  const [selected, setSelected] = useState<ComponentId | null>("engine");
  const [mappedIds, setMappedIds] = useState<ComponentId[]>([]);
  const [closing, setClosing] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const back = useRef<HTMLButtonElement>(null);
  const timer = useRef<number | undefined>(undefined);
  const reason = engineBayAvailability(options.engineBay, options.vehicle);
  const asset = reason ? null : options.engineBay;
  const photo = options.photo === undefined ? engineBayPhoto : options.photo;
  const close = useCallback(() => {
    setClosing(true);
    if (timer.current !== undefined) return;
    const reduced = window.matchMedia?.(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    timer.current = window.setTimeout(onClose, reduced ? 0 : 180);
  }, [onClose]);
  useEffect(() => {
    const origin =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    const app = document.getElementById("root");
    const previousInert = app?.inert;
    const overflow = document.body.style.overflow;
    if (app) app.inert = true;
    document.body.style.overflow = "hidden";
    back.current?.focus();
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        close();
      }
      if (event.key !== "Tab") return;
      const items = Array.from(
        root.current?.querySelectorAll<HTMLElement>(
          'button:not(:disabled), a[href], canvas[tabindex="0"]',
        ) || [],
      );
      const first = items[0],
        last = items.at(-1);
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", keyboard);
    return () => {
      document.removeEventListener("keydown", keyboard);
      if (timer.current !== undefined) window.clearTimeout(timer.current);
      if (app) app.inert = previousInert || false;
      document.body.style.overflow = overflow;
      if (origin?.isConnected) origin.focus({ preventScroll: true });
    };
  }, [close]);
  const mapping = asset?.components.find(
    (component) => component.id === selected,
  );
  return createPortal(
    <div
      ref={root}
      className={`engine-inspector${closing ? " is-closing" : ""}`}
      role="dialog"
      aria-modal="true"
      aria-labelledby="engine-inspector-title"
      lang="en"
    >
      <div className="engine-inspector-shell">
        <header className="engine-inspector-header">
          <button ref={back} className="button secondary" onClick={close}>
            <ArrowLeft size={17} /> Back to Vehicle
          </button>
          <div>
            <span className="engine-overline">Vehicle inspection</span>
            <h2 id="engine-inspector-title">Engine Bay</h2>
          </div>
          <p>
            {options.vehicle.manufacturer} {options.vehicle.model} ·{" "}
            {options.vehicle.model_year} · {options.vehicle.engine}
          </p>
        </header>
        <div className="engine-inspector-grid">
          <section
            className="engine-inspection-main"
            aria-label="Inspection view"
          >
            {photo ? (
              <EngineBayPhotoViewer
                asset={photo}
                selected={selected}
                onSelect={setSelected}
              />
            ) : asset ? (
              <EngineBayViewport
                asset={asset}
                selected={selected}
                onSelect={setSelected}
                onMapped={setMappedIds}
                onViewChange={options.onInspectionViewChange}
              />
            ) : (
              <div className="engine-missing" role="status">
                <Box size={38} strokeWidth={1.2} aria-hidden="true" />
                <span className="engine-overline">Verified asset required</span>
                <h3>Engine bay asset unavailable</h3>
                <p>{reason}</p>
                <p>
                  The exterior is {exteriorName}. Its engine is not used as a
                  Golf Plus inspection model.
                </p>
                <small>
                  No component positions or technical documentation have been
                  inferred from this exterior.
                </small>
              </div>
            )}
            <section
              className="engine-topic-section"
              aria-label="Engine component topics"
            >
              <h3>
                {photo
                  ? "Explore components"
                  : asset
                    ? "Inspection components"
                    : "Component topics"}
              </h3>
              {photo && (
                <p>
                  Photo markers identify only reviewed visible features in this
                  image. Other components are available as information cards;
                  their positions have not been inferred.
                </p>
              )}
              {!photo && !asset && (
                <p>
                  General information only. These topics do not identify
                  locations in a 3D engine bay.
                </p>
              )}
              <div className="engine-topic-list">
                {(Object.keys(componentTopics) as ComponentId[]).map((id) => (
                  <button
                    key={id}
                    onClick={() => setSelected(id)}
                    aria-pressed={selected === id}
                    aria-label={`${componentTopics[id].name} ${photo?.hotspots.some((spot) => spot.id === id) ? "Photo location" : mappedIds.includes(id) ? "3D mapping" : "General topic"}`}
                  >
                    {componentTopics[id].name}
                    <span>
                      {photo?.hotspots.some((spot) => spot.id === id)
                        ? "Photo location"
                        : mappedIds.includes(id)
                          ? "3D mapping"
                          : "General topic"}
                    </span>
                  </button>
                ))}
              </div>
            </section>
          </section>
          <ComponentInfoPanel
            id={selected}
            options={options}
            evidence={mapping?.evidence}
            photoContext={
              photo && selected === "engine-cover"
                ? "The decorative engine cover is removed in this reference photograph; no cover hotspot is shown."
                : photo &&
                    selected &&
                    !photo.hotspots.some((spot) => spot.id === selected)
                  ? "No position is identified for this component in the reference photograph."
                  : undefined
            }
            mapped={
              !!selected &&
              (mappedIds.includes(selected) ||
                !!photo?.hotspots.some((spot) => spot.id === selected))
            }
          />
        </div>
      </div>
    </div>,
    document.body,
  );
}
