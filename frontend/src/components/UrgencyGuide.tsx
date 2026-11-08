import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { TriangleAlert, X } from "lucide-react";

const levels = [
  {
    name: "Not assessed",
    tone: "neutral",
    description:
      "No valid symptom assessment is available, or there are no active cases. This does not mean the vehicle has been checked or is safe to drive.",
  },
  {
    name: "Low",
    tone: "low",
    description:
      "A minor, stable symptom with sufficient safety information. The report may recommend monitoring changes; this is not confirmation of driving safety.",
  },
  {
    name: "Moderate",
    tone: "moderate",
    description:
      "Arrange a timely inspection. In the current system, incomplete safety information also sets a minimum of Moderate and requires an inspection before driving again. Read the report for the missing information.",
  },
  {
    name: "High",
    tone: "high",
    description:
      "Professional inspection is required before further driving. Reported loss of power together with an engine warning sets at least High urgency.",
  },
  {
    name: "Critical",
    tone: "critical",
    description:
      "Stop safely. Do not continue driving. Seek professional assistance. Reported hazards such as brake or steering failure, fire or overheating trigger safety rules that the AI cannot downgrade.",
  },
];

export function UrgencyGuide() {
  const [open, setOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descriptionId = useId();
  useEffect(() => {
    if (open) dialog.current?.showModal();
  }, [open]);
  function close() {
    dialog.current?.close();
    setOpen(false);
  }
  return (
    <>
      <button
        type="button"
        className="metric-icon warm urgency-guide-trigger"
        aria-label="Explain estimated urgency levels"
        aria-haspopup="dialog"
        title="Explain estimated urgency levels"
        onClick={() => setOpen(true)}
      >
        <TriangleAlert size={31} strokeWidth={1.7} aria-hidden="true" />
      </button>
      {open &&
        createPortal(
          <dialog
            ref={dialog}
            className="urgency-guide"
            aria-labelledby={titleId}
            aria-describedby={descriptionId}
            onClose={() => setOpen(false)}
            onClick={(event) => {
              if (event.target === event.currentTarget) close();
            }}
          >
            <header>
              <h2 id={titleId}>Estimated urgency explained</h2>
              <button
                type="button"
                className="urgency-guide-close"
                aria-label="Close urgency explanation"
                onClick={close}
              >
                <X size={22} aria-hidden="true" />
              </button>
            </header>
            <p id={descriptionId}>
              Urgency is symptom triage, not a validated mechanical diagnosis.
              Follow the driving recommendation in your individual report.
            </p>
            <dl>
              {levels.map((level) => (
                <div key={level.name}>
                  <dt>
                    <span className={`badge ${level.tone}`}>{level.name}</span>
                  </dt>
                  <dd>{level.description}</dd>
                </div>
              ))}
            </dl>
            <p className="urgency-guide-summary">
              The dashboard shows the highest recorded urgency across active
              cases. Resolved cases are excluded, but their original reports are
              preserved. AI assessment uses reported symptoms and retrieved
              evidence when available; deterministic safety rules take priority.
            </p>
          </dialog>,
          document.body,
        )}
    </>
  );
}
