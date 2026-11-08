import { useEffect, useRef, useState } from "react";
import { CircleHelp, PackageSearch, Search } from "lucide-react";
import type { CarApi, ToolResult, Vehicle } from "../api/types";
import { errorText } from "../api/client";
import { Badge, ErrorNotice, Spinner, navigateTabs } from "./ui";
import { ToolResults } from "./ToolResults";

export function PartsPage({
  api,
  vehicle,
  initialComponent = "",
}: {
  api: CarApi;
  vehicle: Vehicle;
  initialComponent?: string;
}) {
  const [tab, setTab] = useState("search");
  const [component, setComponent] = useState(initialComponent);
  const [partId, setPartId] = useState("");
  const [country, setCountry] = useState("ES");
  const [currency, setCurrency] = useState("EUR");
  const [result, setResult] = useState<ToolResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const generation = useRef(0);
  useEffect(() => {
    const clear = () => {
      generation.current += 1;
      setResult(null);
      setPartId("");
      setError("");
      setBusy(false);
    };
    const visibility = () => {
      if (document.visibilityState === "hidden") clear();
    };
    window.addEventListener("pagehide", clear);
    document.addEventListener("visibilitychange", visibility);
    return () => {
      generation.current += 1;
      window.removeEventListener("pagehide", clear);
      document.removeEventListener("visibilitychange", visibility);
    };
  }, []);
  return (
    <div className="parts-layout">
      <section className="panel parts-form">
        <div className="panel-header">
          <PackageSearch size={19} aria-hidden="true" />
          <h2>Parts search</h2>
        </div>
        <div
          className="report-tabs"
          role="tablist"
          aria-label="Parts query type"
          onKeyDown={navigateTabs}
        >
          {[
            ["search", "Search"],
            ["fitment", "Compatibility"],
            ["price", "Prices"],
          ].map(([key, label]) => (
            <button
              key={key}
              id={`parts-tab-${key}`}
              role="tab"
              tabIndex={tab === key ? 0 : -1}
              aria-controls="parts-panel"
              aria-selected={tab === key}
              disabled={busy}
              onClick={() => {
                setTab(key);
                setResult(null);
                setError("");
              }}
            >
              {label}
            </button>
          ))}
        </div>
        <form
          className="panel-body"
          id="parts-panel"
          role="tabpanel"
          aria-labelledby={`parts-tab-${tab}`}
          onSubmit={async (event) => {
            event.preventDefault();
            const requestGeneration = ++generation.current;
            setBusy(true);
            setError("");
            setResult(null);
            try {
              const response =
                tab === "search"
                  ? await api.search({
                      vehicle_id: vehicle.vehicle_id,
                      component: component.trim(),
                      limit: 5,
                    })
                  : tab === "fitment"
                    ? await api.compatibility({
                        vehicle_id: vehicle.vehicle_id,
                        part_id: partId.trim(),
                      })
                    : await api.prices({
                        part_id: partId.trim(),
                        country,
                        currency,
                        quantity: 1,
                      });
              if (requestGeneration === generation.current) setResult(response);
            } catch (e) {
              if (requestGeneration === generation.current)
                setError(errorText(e));
            } finally {
              if (requestGeneration === generation.current) setBusy(false);
            }
          }}
        >
          {tab === "search" ? (
            <>
              <label htmlFor="component">
                Which component are you looking for?
              </label>
              <input
                id="component"
                required
                minLength={2}
                maxLength={80}
                value={component}
                onChange={(e) => setComponent(e.target.value)}
                placeholder="For example, glow plugs"
                disabled={busy}
              />
              <p className="field-hint">
                You can search using English or Spanish names.{" "}
              </p>
            </>
          ) : (
            <>
              <label htmlFor="part-reference">Part identifier</label>
              <input
                id="part-reference"
                required
                maxLength={100}
                pattern="[A-Za-z0-9._ \/\-]+"
                value={partId}
                onChange={(e) => setPartId(e.target.value)}
                placeholder="Catalog reference"
                disabled={busy}
              />
              <p className="field-hint">
                A reference enables a search; it does not prove
                compatibility.{" "}
              </p>
            </>
          )}
          {tab === "price" && (
            <div className="form-row">
              <div>
                <label htmlFor="country">Country</label>
                <input
                  id="country"
                  value={country}
                  onChange={(e) => setCountry(e.target.value.toUpperCase())}
                  required
                  pattern="[A-Z]{2}"
                  maxLength={2}
                  disabled={busy}
                />
              </div>
              <div>
                <label htmlFor="currency">Currency</label>
                <input
                  id="currency"
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value.toUpperCase())}
                  required
                  pattern="[A-Z]{3}"
                  maxLength={3}
                  disabled={busy}
                />
              </div>
            </div>
          )}
          {tab === "fitment" && !vehicle.engine_code && (
            <div className="info-note">
              <CircleHelp size={18} aria-hidden="true" />
              <p>
                The engine code is not specified. An engine variant or part
                compatibility cannot be assumed.{" "}
              </p>
            </div>
          )}
          {error && <ErrorNotice text={error} />}
          <button className="button primary" disabled={busy}>
            {busy ? (
              <Spinner label="Searching…" />
            ) : (
              <>
                <Search size={16} aria-hidden="true" />
                {tab === "search"
                  ? "Search candidates"
                  : tab === "fitment"
                    ? "Check compatibility"
                    : "Check prices"}
              </>
            )}
          </button>
        </form>
        <div className="parts-caution">
          This does not replace an inspection. Finding a part does not mean it
          needs replacement.{" "}
        </div>
      </section>
      <section className="panel parts-results" aria-label="Parts results">
        <div className="panel-header">
          <h2>Consultation results</h2>
          <Badge>With provenance</Badge>
        </div>
        {result ? (
          <div className="panel-body">
            <ToolResults results={[result]} />
            {(result.provider === "ebay" ||
              result.provider === "ebay_sandbox") && (
              <p className="fine-print">
                Temporary offers only. These results are not saved in diagnostic
                history and are cleared when you leave or hide this page.
              </p>
            )}
            {tab === "search" &&
              result.available &&
              result.parts?.map((part) => (
                <button
                  className="button secondary"
                  key={part.part_id}
                  onClick={() => {
                    setPartId(part.part_id);
                    setTab("fitment");
                    setResult(null);
                  }}
                >
                  Check {part.part_id}
                </button>
              ))}
          </div>
        ) : (
          <div className="parts-empty">
            <PackageSearch size={42} strokeWidth={1.2} aria-hidden="true" />
            <h3>Clear data, without assumptions.</h3>
            <p>
              Candidates appear here with their provenance and the information
              needed to verify them.{" "}
            </p>
            <small>
              Without an authorized provider, verified pricing and compatibility
              are unavailable.{" "}
            </small>
          </div>
        )}
      </section>
    </div>
  );
}
