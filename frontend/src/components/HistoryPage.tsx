import { useEffect, useRef, useState } from "react";
import {
  ArrowUpRight,
  CheckCircle2,
  History,
  RotateCcw,
  X,
} from "lucide-react";
import type { CaseSummary, HistoryEntry } from "../api/types";
import { dateLabel } from "../lib/history";
import { Badge } from "./ui";

export function HistoryPage({
  cases,
  busy,
  loading,
  error,
  onOpen,
  onChange,
  onRefresh,
  demo,
}: {
  cases: CaseSummary[];
  busy: boolean;
  loading: boolean;
  error: string;
  onOpen: (entry: HistoryEntry) => void;
  onChange: (
    item: CaseSummary,
    resolve: boolean,
    note?: string,
  ) => Promise<boolean>;
  onRefresh: () => void;
  demo: boolean;
}) {
  const [filter, setFilter] = useState<"all" | "active" | "resolved">("all");
  const [pending, setPending] = useState<CaseSummary | null>(null);
  const [note, setNote] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (pending) dialog.current?.showModal();
    else {
      dialog.current?.close();
      trigger.current?.focus();
    }
  }, [pending]);
  const visible = cases.filter(
    (item) => filter === "all" || item.resolution_status === filter,
  );
  return (
    <section className="panel history-panel" aria-label="Diagnostic history">
      <header className="panel-header">
        <History size={19} aria-hidden="true" />
        <h2>Diagnostic cases</h2>
        <Badge>{cases.length}</Badge>
      </header>
      <div className="panel-body">
        <p className="muted">
          Resolution records your report that a problem has been addressed. It
          does not independently verify a repair or establish that driving is
          safe.
          {demo && " Demo cases are temporary and disappear on reload."}
        </p>
        <div className="case-filters" role="group" aria-label="Filter cases">
          {(["all", "active", "resolved"] as const).map((value) => (
            <button
              key={value}
              className="button secondary"
              aria-pressed={filter === value}
              onClick={() => setFilter(value)}
            >
              {value[0].toUpperCase() + value.slice(1)}
            </button>
          ))}
          <button
            className="button text-button"
            onClick={onRefresh}
            disabled={busy || loading}
          >
            Refresh history
          </button>
        </div>
        {loading && <p role="status">Refreshing case history…</p>}
        {error && !pending && (
          <p className="storage-warning" role="alert">
            {error}
          </p>
        )}
        {!loading && !error && !visible.length && (
          <div className="history-empty">
            <History size={32} aria-hidden="true" />
            <h3>No {filter === "all" ? "saved" : filter} cases</h3>
            <p>
              Completed assessments appear here. Existing reports are retained
              when a case is resolved.
            </p>
          </div>
        )}
        <div className="history-list">
          {visible.map((item, index) => (
            <article
              className="case-entry"
              data-case-id={item.conversation_id}
              key={item.conversation_id}
              aria-label={`Case ${index + 1}`}
            >
              <div className="case-heading">
                <strong>Consultation · {dateLabel(item.created_at)}</strong>
                <Badge
                  tone={
                    item.resolution_status === "resolved" ? "teal" : "amber"
                  }
                >
                  {item.resolution_status === "resolved"
                    ? "Resolved"
                    : "Active"}
                </Badge>
              </div>
              <p>{item.summary}</p>
              <p className={`case-urgency ${item.historical_urgency}`}>
                Highest recorded diagnostic urgency:{" "}
                <strong>{item.historical_urgency}</strong>
                {item.historical_urgency === "critical" &&
                  " · Original critical safety warnings remain in the reports."}
              </p>
              {item.resolved_at && (
                <p>
                  Resolved on {dateLabel(item.resolved_at, true)} · User
                  reported
                </p>
              )}
              {item.resolution_note && (
                <p className="resolution-note">
                  Resolution note: {item.resolution_note}
                </p>
              )}
              <div className="case-actions">
                <button
                  className="button secondary"
                  disabled={busy}
                  onClick={() =>
                    onOpen({
                      conversationId: item.conversation_id,
                      vehicleId: item.vehicle_id,
                      createdAt: item.created_at,
                    })
                  }
                >
                  Open reports <ArrowUpRight size={15} aria-hidden="true" />
                </button>
                {item.resolution_status === "active" ? (
                  <button
                    className="button secondary"
                    disabled={busy || loading}
                    onClick={(event) => {
                      trigger.current = event.currentTarget;
                      setNote("");
                      setPending(item);
                    }}
                  >
                    <CheckCircle2 size={16} aria-hidden="true" />
                    Mark as Resolved
                  </button>
                ) : (
                  <button
                    className="button secondary"
                    disabled={busy || loading}
                    onClick={() => void onChange(item, false)}
                  >
                    <RotateCcw size={16} aria-hidden="true" />
                    Reopen Diagnosis
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      </div>
      <dialog
        ref={dialog}
        className="resolution-dialog"
        aria-labelledby="resolution-title"
        onCancel={(event) => {
          if (busy) event.preventDefault();
          else setPending(null);
        }}
      >
        {pending && (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              if (!pending || busy) return;
              void onChange(pending, true, note.trim() || undefined).then(
                (saved) => {
                  if (saved) setPending(null);
                },
              );
            }}
          >
            <div className="case-heading">
              <h2 id="resolution-title">Mark this case as resolved?</h2>
              <button
                type="button"
                className="icon-button"
                aria-label="Cancel resolution"
                disabled={busy}
                onClick={() => setPending(null)}
              >
                <X size={18} />
              </button>
            </div>
            <p>
              This records your report that the problem has been addressed. It
              does not independently verify the repair or establish that the
              vehicle is safe to drive.
            </p>
            <p>
              The original reports and safety warnings will be retained. New
              reported symptoms can make this case active again.
            </p>
            <label htmlFor="resolution-note">Resolution note (optional)</label>
            <textarea
              id="resolution-note"
              value={note}
              maxLength={1000}
              rows={3}
              disabled={busy}
              onChange={(event) => setNote(event.target.value)}
            />
            {error && <p role="alert">{error}</p>}
            <div className="case-actions">
              <button
                type="button"
                className="button secondary"
                disabled={busy}
                onClick={() => setPending(null)}
              >
                Cancel
              </button>
              <button type="submit" className="button primary" disabled={busy}>
                {busy ? "Saving…" : "Confirm Resolution"}
              </button>
            </div>
          </form>
        )}
      </dialog>
    </section>
  );
}
