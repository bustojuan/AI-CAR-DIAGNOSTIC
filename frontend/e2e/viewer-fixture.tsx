// Test-only entry. Not an application route or a production build entry.
import { useCallback, useRef } from "react";
import { createRoot } from "react-dom/client";
import { Vehicle3DViewer } from "../src/components/Vehicle3DViewer";
import type {
  EngineBayAsset,
  VehicleView,
} from "../src/components/vehicle3d/types";
import { dashboardVehicleModel } from "../src/components/vehicle3d/asset";
import "../src/styles.css";

function Fixture() {
  const output = useRef<HTMLOutputElement>(null);
  const inspectionOutput = useRef<HTMLOutputElement>(null);
  const historyOutput = useRef<HTMLOutputElement>(null);
  const actionOutput = useRef<HTMLOutputElement>(null);
  const history = useRef<VehicleView[]>([]);
  const onViewChange = useCallback((next: VehicleView) => {
    if (output.current) output.current.textContent = JSON.stringify(next);
    history.current.push(next);
    if (history.current.length > 200) history.current.shift();
    if (historyOutput.current)
      historyOutput.current.textContent = JSON.stringify(history.current);
  }, []);
  const scenario = new URLSearchParams(location.search).get("case");
  const missing = scenario === "missing";
  const vehicle = scenario === "vehicle";
  const inspection = scenario?.startsWith("engine") || false;
  const identity = {
    manufacturer: "TEST",
    model: "Synthetic calibration",
    model_year: 2009,
    engine: "TEST",
    engine_code: "TEST",
  };
  const engineAsset: EngineBayAsset = {
    model: {
      src: "/e2e/fixtures/engine-calibration.gltf",
      name: "Synthetic engine mapping fixture — NOT AN ENGINE",
      author: "Project",
      license: "Original test fixture",
    },
    vehicle: {
      ...identity,
      engine_code: scenario === "engine-mismatch" ? "OTHER" : "TEST",
    },
    verified: true,
    verifiedBy: "Test harness only, never production configuration",
    components: [
      { id: "battery", meshNames: ["FixtureBattery"], evidence: [] },
      { id: "engine", meshNames: ["FixtureEngine"], evidence: [] },
      { id: "coolant", meshNames: ["FixtureCoolant"], evidence: [] },
      { id: "air-filter", meshNames: ["FixtureAirFilter"], evidence: [] },
    ],
  };
  return (
    <div style={{ padding: 20, minHeight: 1500 }}>
      <h1 style={{ fontSize: 22 }}>3D controls test</h1>
      <p>
        {vehicle
          ? "Demonstration Golf VIII GTI test. It does not represent the Golf Plus."
          : "Synthetic calibration geometry. It is not a vehicle and does not replace the Golf Plus."}
      </p>
      <div
        className="test-viewer"
        style={{ position: "relative", width: "min(800px, 100%)", height: 400 }}
      >
        <Vehicle3DViewer
          model={
            vehicle
              ? dashboardVehicleModel
              : {
                  src: missing
                    ? "/e2e/fixtures/not-found.gltf"
                    : "/e2e/fixtures/orbit-calibration.gltf",
                  name: "Synthetic test geometry",
                  author: "Project · original fixture",
                  license: "Repository test fixture only",
                  hoodMeshNames: inspection ? ["CalibrationHood"] : undefined,
                }
          }
          onViewChange={onViewChange}
          explorer={
            inspection || vehicle
              ? {
                  vehicle: identity,
                  engineBay: inspection ? engineAsset : null,
                  // These tests intentionally exercise the optional future 3D
                  // scene; production uses the licensed photograph by default.
                  photo: null,
                  onAskAI: (draft) => {
                    if (actionOutput.current)
                      actionOutput.current.textContent = draft;
                  },
                  onFindParts: (component) => {
                    if (actionOutput.current)
                      actionOutput.current.textContent = component;
                  },
                  onInspectionViewChange: (view) => {
                    if (inspectionOutput.current)
                      inspectionOutput.current.textContent =
                        JSON.stringify(view);
                  },
                }
              : undefined
          }
        />
      </div>
      <output
        ref={output}
        data-testid="camera"
        style={{ display: "block", overflowWrap: "anywhere", fontSize: 10 }}
      >
        null
      </output>
      <output
        ref={inspectionOutput}
        data-testid="inspection-camera"
        style={{ display: "block", overflowWrap: "anywhere", fontSize: 10 }}
      >
        null
      </output>
      <output
        ref={historyOutput}
        data-testid="camera-history"
        style={{ display: "none" }}
      >
        []
      </output>
      <output
        ref={actionOutput}
        data-testid="component-action"
        style={{ display: "block", overflowWrap: "anywhere", fontSize: 10 }}
      />
      <style>{`.test-viewer .car-illustration {height:100%;object-fit:contain;}`}</style>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<Fixture />);
