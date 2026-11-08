import { ArrowRight, MessageSquare, PackageSearch } from "lucide-react";
import { safeLink } from "../../lib/history";
import { componentDraft, componentTopics } from "./components";
import type {
  ComponentId,
  EngineExplorerOptions,
  TechnicalEvidence,
} from "./types";

export function ComponentInfoPanel({
  id,
  options,
  evidence = [],
  mapped = false,
  photoContext,
}: {
  id: ComponentId | null;
  options: EngineExplorerOptions;
  evidence?: TechnicalEvidence[];
  mapped?: boolean;
  photoContext?: string;
}) {
  if (!id)
    return (
      <aside className="engine-info" aria-label="Component information">
        <MessageSquare size={28} aria-hidden="true" />
        <h3>Select a component</h3>
        <p>
          Select a photo marker or a component card to view its function and
          related symptoms.
        </p>
        <p>Unmapped topics do not identify a position in your engine bay.</p>
      </aside>
    );
  const topic = componentTopics[id];
  return (
    <aside
      className="engine-info"
      aria-label="Component information"
      aria-live="polite"
    >
      <span className="engine-overline">
        {mapped
          ? "Visible inspection feature · illustrative layout"
          : "General component topic"}
      </span>
      <h3>{topic.name}</h3>
      <p className="engine-context">
        General information. These symptoms have several possible causes and do
        not confirm a fault.
      </p>
      {photoContext && <p className="engine-context">{photoContext}</p>}
      <h4>Function</h4>
      <p>{topic.function}</p>
      <h4>Common related symptoms</h4>
      <ul>
        {topic.symptoms.map((symptom) => (
          <li key={symptom}>{symptom}</li>
        ))}
      </ul>
      <h4>Available technical evidence</h4>
      {evidence.length ? (
        <ul>
          {evidence.map((item) => {
            const href = safeLink(item.url);
            return (
              <li key={item.url}>
                {href ? (
                  <a href={href} target="_blank" rel="noreferrer">
                    {item.title}
                  </a>
                ) : (
                  item.title
                )}
                <small>{item.publisher}</small>
              </li>
            );
          })}
        </ul>
      ) : (
        <p>
          No vehicle-specific technical evidence is linked to this component. No
          workshop documentation is implied.
        </p>
      )}
      <div className="engine-component-actions">
        <button
          className="button primary"
          disabled={!options.onAskAI}
          onClick={() => options.onAskAI?.(componentDraft(id, options.vehicle))}
        >
          <MessageSquare size={16} aria-hidden="true" /> Ask AI About This
          Component <ArrowRight size={15} aria-hidden="true" />
        </button>
        <button
          className="button secondary"
          disabled={!options.onFindParts}
          onClick={() => options.onFindParts?.(topic.partsQuery)}
        >
          <PackageSearch size={16} aria-hidden="true" /> Find Related Parts
        </button>
        <small>
          Actions prepare a question or parts search for your diagnostic
          vehicle. They do not submit symptoms, confirm compatibility or provide
          prices automatically.
        </small>
      </div>
    </aside>
  );
}
