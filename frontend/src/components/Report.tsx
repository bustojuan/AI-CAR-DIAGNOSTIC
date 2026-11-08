import { useState } from "react";
import {
  ArrowDownToLine,
  ArrowUpRight,
  Check,
  ClipboardList,
  FileText,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import type { Diagnostic } from "../api/types";
import { dateLabel } from "../lib/history";
import { Badge, SourceLink, navigateTabs } from "./ui";
import { ToolResults } from "./ToolResults";

const urgency = {
  low: "Low",
  moderate: "Moderate",
  high: "High",
  critical: "Critical",
};
const driving = {
  stop_safely_do_not_drive: "Stop safely. Do not continue driving.",
  inspection_before_driving: "Request an inspection before driving again.",
  caution_and_monitor: "Remain cautious and monitor any changes.",
};
const evidenceTypes = {
  official_manufacturer: "Manufacturer",
  third_party_technical: "Third-party reference",
  generic_reference: "Generic reference",
  internal_demo: "Demo document",
};

function download(report: Diagnostic, demo: boolean) {
  const exported = demo
    ? {
        demo_data: true,
        notice:
          "Synthetic UI example without AI execution or a real diagnosis.",
        report,
      }
    : report;
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(exported, null, 2)], { type: "application/json" }),
  );
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${demo ? "demo-" : ""}report-${report.diagnostic_id}.json`;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function Report({
  report,
  demo = false,
  expanded = false,
  initialTab = "resumen",
}: {
  report: Diagnostic | null;
  demo?: boolean;
  expanded?: boolean;
  initialTab?: "resumen" | "comprobaciones" | "fuentes";
}) {
  const [tab, setTab] = useState<string>(initialTab);
  return (
    <section className="panel report-panel" aria-label="Guidance report">
      <header className="panel-header">
        <span className="panel-icon">
          <ClipboardList size={18} aria-hidden="true" />
        </span>
        <h2>
          {initialTab === "fuentes" ? "Consultation sources" : "Your report"}
        </h2>
        <Badge>Guidance</Badge>
        {report && (
          <button
            className="icon-button"
            onClick={() => download(report, demo)}
            aria-label="Download report as JSON"
            title="Download report"
          >
            <ArrowDownToLine size={17} />
          </button>
        )}
      </header>
      {!report ? (
        <div className="report-empty">
          <div className="empty-document">
            <FileText size={36} strokeWidth={1.3} aria-hidden="true" />
            <span>
              <Check size={14} />
            </span>
          </div>
          <h3>
            {initialTab === "fuentes"
              ? "No evidence retrieved yet."
              : "First, tell us what you notice."}
          </h3>
          <p>
            {initialTab === "fuentes"
              ? "Sources will appear here with their provenance and limitations. No manufacturer documentation has been verified for this consultation."
              : "Your report will use what you tell us. No fault is treated as confirmed."}
          </p>
          <ol className="report-steps">
            <li>
              <span>01</span>
              <div>
                <strong>Understand the symptoms</strong>
                <small>What happens and under which conditions.</small>
              </div>
            </li>
            <li>
              <span>02</span>
              <div>
                <strong>Assess urgency</strong>
                <small>Safety comes first.</small>
              </div>
            </li>
            <li>
              <span>03</span>
              <div>
                <strong>Prepare the next step</strong>
                <small>Hypotheses, checks and sources.</small>
              </div>
            </li>
          </ol>
          <div className="report-empty-foot">
            <ShieldCheck size={15} aria-hidden="true" />
            You provide observations. Inspection confirms the cause.{" "}
          </div>
        </div>
      ) : (
        <>
          <div
            className={`urgency-banner ${report.urgency_level}`}
            role={report.urgency_level === "critical" ? "alert" : "status"}
          >
            <ShieldAlert size={22} aria-hidden="true" />
            <div>
              <span>Diagnostic urgency: {urgency[report.urgency_level]}</span>
              <strong>{driving[report.driving_recommendation]}</strong>
            </div>
          </div>
          {demo && (
            <p className="report-demo">
              Illustrative UI report. It does not assess a real vehicle.{" "}
            </p>
          )}
          {!expanded && (
            <div
              className="report-tabs"
              role="tablist"
              aria-label="Report sections"
              onKeyDown={navigateTabs}
            >
              {[
                ["resumen", "Overview"],
                ["comprobaciones", "Next steps"],
                ["fuentes", "Sources and limits"],
              ].map(([key, label]) => (
                <button
                  key={key}
                  id={`tab-${key}`}
                  role="tab"
                  tabIndex={tab === key ? 0 : -1}
                  aria-selected={tab === key}
                  aria-controls={`panel-${key}`}
                  onClick={() => setTab(key)}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
          <div
            className="report-content"
            role={expanded ? undefined : "tabpanel"}
            id={expanded ? undefined : `panel-${tab}`}
            aria-labelledby={expanded ? undefined : `tab-${tab}`}
            tabIndex={0}
          >
            {(expanded || tab === "resumen") && (
              <>
                <p className="report-summary">{report.summary}</p>
                <section
                  className="urgency-detail"
                  aria-label="Urgency assessment details"
                >
                  <h3>Why this urgency?</h3>
                  <p>
                    {report.urgency_assessment?.explanation ||
                      "Additional urgency details were not recorded for this historical report."}
                  </p>
                  {report.urgency_assessment && (
                    <>
                      <h4>Detected warning signs</h4>
                      {report.urgency_assessment.warning_signs.length ? (
                        <ul>
                          {report.urgency_assessment.warning_signs.map(
                            (sign, i) => (
                              <li key={i}>{sign}</li>
                            ),
                          )}
                        </ul>
                      ) : (
                        <p>
                          No warning signs were identified in the supplied
                          observations. This does not establish safety.
                        </p>
                      )}
                      <h4>Missing safety information</h4>
                      {report.urgency_assessment.missing_safety_information
                        .length ? (
                        <ul>
                          {report.urgency_assessment.missing_safety_information.map(
                            (item, i) => (
                              <li key={i}>{item}</li>
                            ),
                          )}
                        </ul>
                      ) : (
                        <p>
                          No additional safety information was flagged. The
                          observations remain unverified.
                        </p>
                      )}
                    </>
                  )}
                  <p>
                    <strong>Driving recommendation: </strong>
                    {driving[report.driving_recommendation]}
                  </p>
                  <p>
                    <strong>Professional assistance recommended: </strong>
                    {report.professional_assistance_recommended
                      ? "Yes"
                      : "Not currently flagged; seek help if symptoms persist or change."}
                  </p>
                  <small>
                    Symptom triage only. This is not a validated mechanical
                    diagnosis.
                  </small>
                </section>
                {
                  <div className="detected-symptoms">
                    <h3>Reported symptoms</h3>
                    {report.extracted_symptoms.length ? (
                      <ul>
                        {report.extracted_symptoms.map((symptom, i) => (
                          <li key={i}>{symptom}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="muted">
                        No structured symptoms were extracted.{" "}
                      </p>
                    )}
                  </div>
                }
                {report.professional_assistance_recommended && (
                  <p className="professional-note">
                    <ShieldCheck size={16} aria-hidden="true" />
                    Professional inspection is recommended.{" "}
                  </p>
                )}
                {!!report.possible_causes.length && (
                  <>
                    <div className="section-heading">
                      <h3>Possible causes</h3>
                      <small>Unconfirmed</small>
                    </div>
                    {report.possible_causes.map((cause, i) => (
                      <details
                        className="hypothesis"
                        key={i}
                        open={expanded || i === 0}
                      >
                        <summary>
                          <span className="hypothesis-number">
                            {String(i + 1).padStart(2, "0")}
                          </span>
                          <span>
                            {cause.component_or_system}
                            <small>
                              Hypothesis ·{" "}
                              {cause.uncertainty === "insufficient_evidence"
                                ? "insufficient evidence"
                                : cause.uncertainty === "uncertain"
                                  ? "uncertain"
                                  : "possible"}
                            </small>
                          </span>
                          <ArrowUpRight size={16} aria-hidden="true" />
                        </summary>
                        <div>
                          <p>{cause.possible_failure}</p>
                          <h4>Supporting observations</h4>
                          <ul>
                            {cause.supporting_symptoms.map((s, j) => (
                              <li key={j}>{s}</li>
                            ))}
                          </ul>
                          <h4>What remains to be checked</h4>
                          <ul>
                            {cause.missing_or_contradictory_evidence.map(
                              (s, j) => (
                                <li key={j}>{s}</li>
                              ),
                            )}
                          </ul>
                          <p className="verification">
                            {cause.recommended_verification}
                          </p>
                        </div>
                      </details>
                    ))}
                  </>
                )}
                {!!report.follow_up_questions.length && (
                  <div className="follow-up">
                    <h3>To refine the guidance</h3>
                    <p>You can answer in the conversation.</p>
                    <ul>
                      {report.follow_up_questions.map((q, i) => (
                        <li key={i}>{q}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {!!report.tool_results?.length && (
                  <>
                    <h3 className="section-title">Queried parts</h3>
                    <ToolResults results={report.tool_results} />
                  </>
                )}
              </>
            )}
            {(expanded || tab === "comprobaciones") && (
              <>
                <h3>Recommended checks</h3>
                <p className="muted">
                  Do not attempt repairs or dismantling yourself.{" "}
                </p>
                {report.recommended_checks.map((check, i) => (
                  <div className="check-item" key={i}>
                    <Badge
                      tone={
                        check.category === "safe_observation" ? "teal" : "amber"
                      }
                    >
                      {check.category === "safe_observation"
                        ? "Safe observation"
                        : check.category === "professional"
                          ? "Professional"
                          : "Technical check"}
                    </Badge>
                    <p>{check.description}</p>
                  </div>
                ))}
                <h3 className="section-title">Next steps</h3>
                <ol className="next-steps">
                  {report.next_steps.map((step, i) => (
                    <li key={i}>{step}</li>
                  ))}
                </ol>
              </>
            )}
            {(expanded || tab === "fuentes") && (
              <>
                <h3>Available evidence</h3>
                <p className="muted">
                  A generic or demo reference is not verified manufacturer
                  documentation.{" "}
                </p>
                {!report.citations?.length && (
                  <div className="empty-source">
                    <FileText size={22} aria-hidden="true" />
                    <p>
                      No technical documentation has been retrieved for this
                      report.{" "}
                    </p>
                  </div>
                )}
                {report.citations?.map((source) => (
                  <article className="citation" key={source.chunk_id}>
                    <Badge
                      tone={
                        source.evidence_type === "internal_demo"
                          ? "amber"
                          : "neutral"
                      }
                    >
                      {evidenceTypes[source.evidence_type]}
                    </Badge>
                    <h4>{source.document_title}</h4>
                    <p>
                      {source.publisher || "Publisher not supplied"}
                      {source.page ? ` · Page ${source.page}` : ""}
                      {source.section ? ` · ${source.section}` : ""}
                    </p>
                    <p>Source verification: {source.verification_status}</p>
                    <SourceLink url={source.source_url} />
                  </article>
                ))}
                <ul className="evidence-list">
                  {report.evidence_sources.map((source, i) => (
                    <li key={i}>
                      <strong>
                        {source.kind === "user_provided"
                          ? "User observations"
                          : source.kind === "general_model_knowledge"
                            ? "Unverified general model knowledge"
                            : source.kind === "external_tool_result"
                              ? "External tool result"
                              : "Retrieved technical reference"}
                      </strong>
                      <p>{source.description}</p>
                    </li>
                  ))}
                </ul>
                <h3>Limitations</h3>
                <ul className="limitations">
                  {report.limitations.map((text, i) => (
                    <li key={i}>{text}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
          <footer className="report-footer">
            <span>{dateLabel(report.created_at)}</span>
            <span>Hypothesis ≠ confirmed diagnosis</span>
          </footer>
        </>
      )}
    </section>
  );
}
