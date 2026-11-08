import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type PointerEvent,
} from "react";
import { Move, RotateCcw, ZoomIn, ZoomOut } from "lucide-react";
import type { ComponentId, EngineBayPhoto } from "./types";
import { componentTopics } from "./components";

type View = { scale: number; x: number; y: number };
type Point = { x: number; y: number };
const initial: View = { scale: 1, x: 0, y: 0 };

export function EngineBayPhotoViewer({
  asset,
  selected,
  onSelect,
}: {
  asset: EngineBayPhoto;
  selected: ComponentId | null;
  onSelect: (id: ComponentId) => void;
}) {
  const viewport = useRef<HTMLDivElement>(null);
  const points = useRef(new Map<number, Point>());
  const moved = useRef(false);
  const current = useRef(initial);
  const [view, setView] = useState(initial);
  const [dragging, setDragging] = useState(false);
  const [phase, setPhase] = useState<"loading" | "ready" | "error">("loading");
  const apply = useCallback((next: View) => {
    const bounds = viewport.current?.getBoundingClientRect();
    if (!bounds) return;
    const scale = Math.max(1, Math.min(3.5, next.scale));
    const maxX = (bounds.width * (scale - 1)) / 2;
    const maxY = (bounds.height * (scale - 1)) / 2;
    const result = {
      scale,
      x: Math.max(-maxX, Math.min(maxX, next.x)),
      y: Math.max(-maxY, Math.min(maxY, next.y)),
    };
    current.current = result;
    setView(result);
  }, []);
  const zoom = useCallback(
    (factor: number, anchor: Point = { x: 0, y: 0 }) => {
      const previous = current.current;
      const scale = Math.max(1, Math.min(3.5, previous.scale * factor));
      const ratio = scale / previous.scale;
      apply({
        scale,
        x: anchor.x - (anchor.x - previous.x) * ratio,
        y: anchor.y - (anchor.y - previous.y) * ratio,
      });
    },
    [apply],
  );
  useEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const wheel = (event: WheelEvent) => {
      if (phase !== "ready") return;
      event.preventDefault();
      const bounds = element.getBoundingClientRect();
      zoom(Math.exp(-Math.max(-100, Math.min(100, event.deltaY)) * 0.002), {
        x: event.clientX - bounds.left - bounds.width / 2,
        y: event.clientY - bounds.top - bounds.height / 2,
      });
    };
    element.addEventListener("wheel", wheel, { passive: false });
    const resize =
      typeof ResizeObserver === "undefined"
        ? null
        : new ResizeObserver(() => apply(current.current));
    resize?.observe(element);
    return () => {
      element.removeEventListener("wheel", wheel);
      resize?.disconnect();
    };
  }, [apply, phase, zoom]);
  const move = (event: PointerEvent<HTMLDivElement>) => {
    if (!points.current.has(event.pointerId)) return;
    const before = [...points.current.values()];
    points.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    const after = [...points.current.values()];
    if (before.length === 2 || Math.hypot(event.movementX, event.movementY) > 3)
      moved.current = true;
    const center = (values: Point[]) => ({
      x: values.reduce((n, p) => n + p.x, 0) / values.length,
      y: values.reduce((n, p) => n + p.y, 0) / values.length,
    });
    const oldCenter = center(before),
      newCenter = center(after);
    if (before.length === 2) {
      const distance = (values: Point[]) =>
        Math.hypot(values[0].x - values[1].x, values[0].y - values[1].y);
      const bounds = viewport.current!.getBoundingClientRect();
      zoom(distance(after) / Math.max(1, distance(before)), {
        x: oldCenter.x - bounds.left - bounds.width / 2,
        y: oldCenter.y - bounds.top - bounds.height / 2,
      });
    }
    apply({
      ...current.current,
      x: current.current.x + newCenter.x - oldCenter.x,
      y: current.current.y + newCenter.y - oldCenter.y,
    });
  };
  const release = (event: PointerEvent<HTMLDivElement>) => {
    points.current.delete(event.pointerId);
    setDragging(points.current.size > 0);
  };
  return (
    <figure className="engine-photo-figure">
      <div className="engine-photo-heading">
        <div>
          <span className="engine-overline">Under the hood</span>
          <h3>Explore the complete engine compartment</h3>
        </div>
        <span>Photographic inspection</span>
      </div>
      <p className="engine-photo-notice">{asset.notice}</p>
      <div
        className={`engine-photo-viewport ${dragging ? "is-dragging" : ""}`}
        ref={viewport}
        role="region"
        aria-label="Engine compartment photograph"
        tabIndex={0}
        aria-describedby="engine-photo-instructions"
        style={{ aspectRatio: `${asset.width} / ${asset.height}` }}
        onPointerDown={(event) => {
          if (phase !== "ready") return;
          if (event.pointerType === "mouse" && event.button !== 0) return;
          if (points.current.size >= 2) return;
          if (!points.current.size) moved.current = false;
          if (!(event.target as HTMLElement).closest("button"))
            event.currentTarget.setPointerCapture(event.pointerId);
          points.current.set(event.pointerId, {
            x: event.clientX,
            y: event.clientY,
          });
          setDragging(true);
        }}
        onPointerMove={move}
        onPointerUp={release}
        onPointerCancel={release}
        onLostPointerCapture={release}
        onKeyDown={(event) => {
          if (event.target !== event.currentTarget) return;
          const keys = [
            "ArrowLeft",
            "ArrowRight",
            "ArrowUp",
            "ArrowDown",
            "+",
            "=",
            "-",
            "Home",
          ];
          if (!keys.includes(event.key)) return;
          event.preventDefault();
          if (event.key === "Home") apply(initial);
          else if (["+", "="].includes(event.key)) zoom(1.25);
          else if (event.key === "-") zoom(0.8);
          else
            apply({
              ...current.current,
              x:
                current.current.x +
                (event.key === "ArrowLeft"
                  ? 35
                  : event.key === "ArrowRight"
                    ? -35
                    : 0),
              y:
                current.current.y +
                (event.key === "ArrowUp"
                  ? 35
                  : event.key === "ArrowDown"
                    ? -35
                    : 0),
            });
        }}
      >
        <div
          className="engine-photo-transform"
          style={{
            transform: `translate(${view.x}px, ${view.y}px) scale(${view.scale})`,
          }}
        >
          <img
            src={asset.src}
            alt={asset.alt}
            width={asset.width}
            height={asset.height}
            draggable={false}
            onLoad={() => setPhase("ready")}
            onError={() => setPhase("error")}
            decoding="async"
          />
          {phase === "ready" &&
            asset.hotspots
              .filter(
                (spot) =>
                  spot.review.trim() &&
                  spot.x >= 0 &&
                  spot.x <= 1 &&
                  spot.y >= 0 &&
                  spot.y <= 1,
              )
              .map((spot) => (
                <button
                  key={spot.id}
                  className={`engine-photo-hotspot ${selected === spot.id ? "is-selected" : ""}`}
                  style={{
                    left: `${spot.x * 100}%`,
                    top: `${spot.y * 100}%`,
                    transform: `translate(-50%,-50%) scale(${1 / view.scale})`,
                  }}
                  aria-label={`Inspect ${componentTopics[spot.id].name} in photograph`}
                  aria-pressed={selected === spot.id}
                  onClick={(event) => {
                    if (!moved.current || event.detail === 0) onSelect(spot.id);
                  }}
                >
                  <span aria-hidden="true">+</span>
                  <span>{componentTopics[spot.id].name}</span>
                </button>
              ))}
        </div>
        {phase !== "ready" && (
          <div className="engine-photo-status" role="status">
            {phase === "loading"
              ? "Loading engine compartment photograph…"
              : "The photograph could not be loaded. Component information remains available below."}
          </div>
        )}
      </div>
      <div className="engine-photo-controls">
        <span id="engine-photo-instructions">
          <Move size={15} aria-hidden="true" />
          Drag to pan · scroll or pinch to zoom
        </span>
        <div>
          <button
            aria-label="Zoom out engine bay"
            disabled={phase !== "ready" || view.scale <= 1}
            onClick={() => zoom(0.8)}
          >
            <ZoomOut size={18} />
          </button>
          <output aria-label="Engine bay zoom">
            {Math.round(view.scale * 100)}%
          </output>
          <button
            aria-label="Zoom in engine bay"
            disabled={phase !== "ready" || view.scale >= 3.5}
            onClick={() => zoom(1.25)}
          >
            <ZoomIn size={18} />
          </button>
          <button
            aria-label="Reset engine bay photograph"
            disabled={phase !== "ready"}
            onClick={() => apply(initial)}
          >
            <RotateCcw size={18} />
          </button>
        </div>
      </div>
      <figcaption>
        <span>
          {asset.depictedVehicle} · “{asset.title}” · Photo by {asset.author} ·
          <a href={asset.sourceUrl} target="_blank" rel="noreferrer">
            Source
          </a>{" "}
          ·{" "}
          <a href={asset.licenseUrl} target="_blank" rel="noreferrer">
            {asset.license}
          </a>
        </span>
      </figcaption>
    </figure>
  );
}
