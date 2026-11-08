import { useState } from "react";
import { ArrowUp, ChevronDown, Plus, ShieldCheck } from "lucide-react";
import type { Observation } from "../api/types";
import { ErrorNotice, Spinner } from "./ui";

const suggestions = [
  "It has difficulty starting when cold",
  "I have noticed a loss of power",
  "I hear an unusual noise",
];
export function Composer({
  onSend,
  busy,
  disabled,
  hasMessages,
  initialText = "",
}: {
  onSend: (data: Observation) => Promise<boolean>;
  busy: boolean;
  disabled: boolean;
  hasMessages: boolean;
  initialText?: string;
}) {
  const [text, setText] = useState(initialText);
  const [details, setDetails] = useState(false);
  const [dtcs, setDtcs] = useState("");
  const [warnings, setWarnings] = useState("");
  const [symptoms, setSymptoms] = useState("");
  const [mileage, setMileage] = useState("");
  const [error, setError] = useState("");
  const split = (value: string) =>
    value
      .split(/[,;\n]/)
      .map((s) => s.trim())
      .filter(Boolean);
  return (
    <form
      className="composer-area"
      onSubmit={async (event) => {
        event.preventDefault();
        setError("");
        const codes = split(dtcs).map((code) => code.toUpperCase());
        const lights = split(warnings);
        const symptomsList = split(symptoms);
        if (text.trim().length < 3) {
          setError("Describe the problem using at least three characters.");
          return;
        }
        if (
          codes.length > 20 ||
          codes.some((code) => !/^[PBCU][0-3][0-9A-F]{3}$/.test(code))
        ) {
          setError("Check the OBD codes, for example P0380. Maximum 20.");
          return;
        }
        if (
          [lights, symptomsList].some(
            (list) => list.length > 20 || list.some((s) => s.length > 200),
          )
        ) {
          setError("Enter up to 20 observations of 200 characters each.");
          return;
        }
        if (
          await onSend({
            description: text.trim(),
            dtcs: codes,
            warning_lights: lights,
            symptoms: symptomsList,
            ...(mileage ? { mileage_km: Number(mileage) } : {}),
          })
        ) {
          setText("");
          setDtcs("");
          setWarnings("");
          setSymptoms("");
          setMileage("");
        }
      }}
    >
      {!hasMessages && (
        <div className="suggestions" aria-label="Example symptoms">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => setText(suggestion)}
              disabled={busy || disabled}
            >
              <Plus size={13} aria-hidden="true" />
              {suggestion}
            </button>
          ))}
        </div>
      )}
      <div className={`composer ${busy ? "is-busy" : ""}`}>
        <label htmlFor="description" className="sr-only">
          Describe the symptoms{" "}
        </label>
        <textarea
          id="description"
          required
          minLength={3}
          maxLength={6000}
          rows={3}
          placeholder={
            hasMessages
              ? "Add an observation or answer the questions…"
              : "Tell us what happens, when it started and under which conditions…"
          }
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={busy || disabled}
        />
        <div className="composer-toolbar">
          <button
            type="button"
            className="detail-toggle"
            aria-expanded={details}
            aria-controls="observation-details"
            onClick={() => setDetails(!details)}
            disabled={busy}
          >
            <Plus size={15} aria-hidden="true" />
            Add details <ChevronDown size={13} aria-hidden="true" />
          </button>
          <span className="character-count">{text.length} / 6000</span>
          <button
            className="send-button"
            type="submit"
            disabled={busy || disabled || text.trim().length < 3}
            aria-label={busy ? "Preparing report" : "Send consultation"}
          >
            {busy ? (
              <Spinner label="" />
            ) : (
              <ArrowUp size={21} aria-hidden="true" />
            )}
          </button>
        </div>
      </div>
      {details && (
        <div className="observation-details" id="observation-details">
          <div className="form-row">
            <div>
              <label htmlFor="dtcs">OBD codes</label>
              <input
                id="dtcs"
                value={dtcs}
                maxLength={160}
                onChange={(e) => setDtcs(e.target.value)}
                placeholder="P0380, P0671"
                disabled={busy || disabled}
              />
            </div>
            <div>
              <label htmlFor="observed-mileage">Observed mileage</label>
              <input
                id="observed-mileage"
                type="number"
                min="0"
                max="3000000"
                step="1"
                value={mileage}
                onChange={(e) => setMileage(e.target.value)}
                placeholder="Optional, in km"
                disabled={busy || disabled}
              />
            </div>
          </div>
          <label htmlFor="warning-lights">Warning lights</label>
          <input
            id="warning-lights"
            value={warnings}
            maxLength={4000}
            onChange={(e) => setWarnings(e.target.value)}
            placeholder="Separated by commas"
            disabled={busy || disabled}
          />
          <label htmlFor="extra-symptoms">Other symptoms</label>
          <input
            id="extra-symptoms"
            value={symptoms}
            maxLength={4000}
            onChange={(e) => setSymptoms(e.target.value)}
            placeholder="Separated by commas"
            disabled={busy || disabled}
          />
        </div>
      )}
      {error && <ErrorNotice text={error} />}
      <p className="privacy-hint">
        <ShieldCheck size={13} aria-hidden="true" />
        Do not include your VIN, registration number or personal data.{" "}
      </p>
    </form>
  );
}
