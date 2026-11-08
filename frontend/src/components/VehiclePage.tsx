import { useState } from "react";
import { CarFront, Info, Save } from "lucide-react";
import type { CarApi, Vehicle } from "../api/types";
import { errorText } from "../api/client";
import { Badge, ErrorNotice, Spinner } from "./ui";
import { Vehicle3DViewer } from "./Vehicle3DViewer";
import { dashboardVehicleModel } from "./vehicle3d/asset";

export function VehiclePage({
  vehicle,
  api,
  onSave,
  demo,
}: {
  vehicle: Vehicle;
  api: CarApi;
  onSave: (vehicle: Vehicle) => void;
  demo: boolean;
}) {
  const [engine, setEngine] = useState(vehicle.engine_code || "");
  const [mileage, setMileage] = useState(vehicle.mileage_km?.toString() || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  return (
    <div className="vehicle-layout">
      <section className="panel vehicle-profile">
        <div className="section-heading">
          <span className="eyebrow">YOUR VEHICLE</span>
          <Badge>Supported by MVP</Badge>
        </div>
        <div className="vehicle-profile-viewer">
          <Vehicle3DViewer model={dashboardVehicleModel} />
        </div>
        <h2>
          {vehicle.manufacturer} {vehicle.model}
        </h2>
        <p>
          {vehicle.model_year} · {vehicle.engine}
        </p>
        <div className="vehicle-specs">
          {[
            [
              "Fuel",
              vehicle.fuel_type === "diesel" ? "Diesel" : vehicle.fuel_type,
            ],
            [
              "Transmission",
              vehicle.transmission === "manual"
                ? "Manual"
                : vehicle.transmission,
            ],
            ["Engine code", vehicle.engine_code || "Not specified"],
            ["Gearbox code", "Not confirmed"],
            ["PR codes", "Not confirmed"],
            ["Power", vehicle.power_output || "Not specified"],
          ].map(([k, v]) => (
            <div key={k}>
              <span>{k}</span>
              <strong>{v}</strong>
            </div>
          ))}
        </div>
        <p className="fine-print">
          Vehicle identity is owner-reported. The gearbox code and equipment PR
          codes still require confirmation. Manual transmission does not
          identify a specific gearbox.
        </p>
      </section>
      <section className="panel vehicle-form">
        <div className="panel-header">
          <CarFront size={19} aria-hidden="true" />
          <h2>Add what you know</h2>
        </div>
        <div className="panel-body">
          <p className="muted">
            More information helps identify appropriate checks. Leave unknown
            details blank.{" "}
          </p>
          <form
            onSubmit={async (event) => {
              event.preventDefault();
              setBusy(true);
              setError("");
              setSaved(false);
              try {
                const result = await api.updateVehicle(vehicle.vehicle_id, {
                  engine_code: engine.trim() || null,
                  mileage_km: mileage ? Number(mileage) : null,
                });
                onSave(result);
                setSaved(true);
              } catch (e) {
                setError(errorText(e));
              } finally {
                setBusy(false);
              }
            }}
          >
            <label htmlFor="engine-code">
              Engine code <span>Optional</span>
            </label>
            <input
              id="engine-code"
              value={engine}
              onChange={(e) => {
                setEngine(e.target.value);
                setSaved(false);
              }}
              maxLength={200}
              placeholder="Only if known"
              disabled={busy}
            />
            <p className="field-hint">
              Check the vehicle documentation. The engine code is neither 2.0
              TDI nor the VIN.{" "}
            </p>
            <label htmlFor="vehicle-mileage">
              Mileage <span>Optional</span>
            </label>
            <div className="input-with-unit">
              <input
                id="vehicle-mileage"
                type="number"
                min="0"
                max="3000000"
                step="1"
                value={mileage}
                onChange={(e) => {
                  setMileage(e.target.value);
                  setSaved(false);
                }}
                placeholder="Not specified"
                disabled={busy}
              />
              <span>km</span>
            </div>
            <div className="info-note">
              <Info size={17} aria-hidden="true" />
              <p>
                This interface does not need your VIN or personal data. Exact
                compatibility still requires evidence from an authorized
                provider.{" "}
              </p>
            </div>
            {error && <ErrorNotice text={error} />}
            {saved && (
              <p className="save-success" role="status">
                {demo
                  ? "Example changes saved in memory."
                  : "Vehicle details updated."}
              </p>
            )}
            <button className="button primary" type="submit" disabled={busy}>
              {busy ? (
                <Spinner label="Saving…" />
              ) : (
                <>
                  <Save size={16} aria-hidden="true" />
                  Save changes{" "}
                </>
              )}
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}
