import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Info, X } from "lucide-react";
import { dashboardVehicleModel } from "./asset";
import type { VehicleModelAsset } from "./types";

export function AssetCreditsContent({
  model = dashboardVehicleModel,
}: {
  model?: VehicleModelAsset | null;
}) {
  if (!model) return null;
  const selectedGolf = model.src === "/models/golf-viii-gti.glb";
  return (
    <div className="asset-credits-content">
      <h3>{model.name}</h3>
      <p>
        {selectedGolf
          ? "The approved MVP visual represents a Volkswagen Golf VIII GTI, not an exact Golf Plus. Vehicle specifications, diagnostics and documentation refer to the configured Golf Plus, independently of this visual. The loading and fallback image is a render of the same 3D model."
          : model.notice}
      </p>
      <dl>
        <dt>Author</dt>
        <dd>
          {model.author}
          {selectedGolf && (
            <>. Embedded author credit: GT Cars: Hyperspeed (Car2022).</>
          )}
        </dd>
        {model.sourceUrl && (
          <>
            <dt>Original source</dt>
            <dd>
              <a href={model.sourceUrl} target="_blank" rel="noreferrer">
                {selectedGolf
                  ? "Volkswagen Golf 8. GTI (A8) on Sketchfab"
                  : model.name}
              </a>
            </dd>
          </>
        )}
        <dt>License</dt>
        <dd>
          {model.license === "CC BY 4.0" ? (
            <a
              href="https://creativecommons.org/licenses/by/4.0/"
              target="_blank"
              rel="noreferrer"
            >
              {model.license}
            </a>
          ) : (
            model.license
          )}
        </dd>
      </dl>
      {selectedGolf && (
        <p>
          Distributed by{" "}
          <a
            href="https://github.com/pedrosoandre/carros"
            target="_blank"
            rel="noreferrer"
          >
            pedrosoandre/carros
          </a>
          . The distributor reports geometry optimization and Meshopt
          compression. The supplied GLB is unchanged by this application;
          viewing orientation, lighting and the fallback render are provided by
          the application. See{" "}
          <a
            href="/models/GOLF-DISTRIBUTOR-LICENSE.md"
            target="_blank"
            rel="noreferrer"
          >
            provenance and prior modifications
          </a>
          . Attribution does not imply endorsement.
        </p>
      )}
    </div>
  );
}

export function AssetCredits({
  model = dashboardVehicleModel,
  compact = true,
}: {
  model?: VehicleModelAsset | null;
  compact?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    if (open) dialog.current?.showModal();
  }, [open]);
  function close() {
    dialog.current?.close();
    setOpen(false);
  }
  if (!model) return null;
  return (
    <>
      <button
        type="button"
        className={`asset-credits-trigger${compact ? " is-compact" : ""}`}
        aria-label="Asset Credits — visual model information"
        title="Asset Credits — visual model information"
        aria-haspopup="dialog"
        onClick={() => setOpen(true)}
      >
        <Info size={16} aria-hidden="true" />
        {!compact && <span>Asset Credits</span>}
      </button>
      {open &&
        createPortal(
          <dialog
            ref={dialog}
            className="asset-credits-dialog"
            aria-labelledby={titleId}
            onClose={() => setOpen(false)}
            onClick={(event) => {
              if (event.target === event.currentTarget) close();
            }}
          >
            <header>
              <h2 id={titleId}>Asset Credits</h2>
              <button
                type="button"
                className="asset-credits-close"
                aria-label="Close Asset Credits"
                onClick={close}
              >
                <X size={22} aria-hidden="true" />
              </button>
            </header>
            <AssetCreditsContent model={model} />
          </dialog>,
          document.body,
        )}
    </>
  );
}
