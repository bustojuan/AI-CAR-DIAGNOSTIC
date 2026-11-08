import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  Home,
  Settings2,
  FileText,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  CarFront,
  ChevronRight,
  CircleHelp,
  FlaskConical,
  History,
  Menu,
  MessageSquare,
  Info,
  PackageSearch,
  Plus,
  RotateCw,
  ShieldCheck,
  Wrench,
  X,
} from "lucide-react";
import { ApiError, createApi, errorText } from "./api/client";
import type {
  CarApi,
  CaseSummary,
  VehicleUrgency,
  Diagnostic,
  Health,
  HistoryEntry,
  Observation,
  ToolsStatus,
  Vehicle,
} from "./api/types";
import { createDemoApi, demoVehicle } from "./demo/api";
import { readHistory, writeHistory } from "./lib/history";
import { Badge, CarIllustration, ErrorNotice, Spinner } from "./components/ui";
import { Report } from "./components/Report";
import { Composer } from "./components/Composer";
import { VehiclePage } from "./components/VehiclePage";
import { HomePage } from "./components/HomePage";
import { HistoryPage } from "./components/HistoryPage";
import { AssessmentSelector } from "./components/AssessmentSelector";
import { PartsPage } from "./components/PartsPage";
import {
  AssetCredits,
  AssetCreditsContent,
} from "./components/vehicle3d/AssetCredits";

type View =
  | "inicio"
  | "diagnostico"
  | "informe"
  | "evidencia"
  | "vehiculo"
  | "recambios"
  | "historial"
  | "configuracion"
  | "ayuda";
type ThreadMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  codes?: string[];
};
const navigation = [
  { key: "inicio", label: "Home", icon: Home },
  { key: "historial", label: "History", icon: History },
  { key: "recambios", label: "Parts", icon: PackageSearch },
  { key: "vehiculo", label: "My Vehicle", icon: CarFront },
] as const;
const viewLabels: Record<View, string> = {
  inicio: "Home",
  diagnostico: "Diagnosis",
  informe: "Report",
  evidencia: "Technical Evidence",
  vehiculo: "My Vehicle",
  recambios: "Parts",
  historial: "History",
  configuracion: "Settings",
  ayuda: "Help",
};
const viewFromHash = (): View => {
  const key = window.location.hash.slice(1);
  return Object.hasOwn(viewLabels, key) ? (key as View) : "inicio";
};
const modeLink = (demo: boolean) => {
  const url = new URL(window.location.href);
  if (demo) url.searchParams.set("demo", "1");
  else url.searchParams.delete("demo");
  url.hash = "inicio";
  return url.href;
};

export function App({
  apiOverride,
  demoOverride,
}: { apiOverride?: CarApi; demoOverride?: boolean } = {}) {
  const demo =
    demoOverride ??
    new URLSearchParams(window.location.search).get("demo") === "1";
  const api = useMemo(
    () => apiOverride || (demo ? createDemoApi() : createApi()),
    [apiOverride, demo],
  );
  const [view, setView] = useState<View>(viewFromHash);
  const [mobileMenu, setMobileMenu] = useState(false);
  const [isMobile, setIsMobile] = useState(() => window.innerWidth <= 1100);
  const [vehicle, setVehicle] = useState<Vehicle | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [tools, setTools] = useState<ToolsStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  const [connectionError, setConnectionError] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [thread, setThread] = useState<ThreadMessage[]>([]);
  const [report, setReport] = useState<Diagnostic | null>(null);
  const [assessmentIds, setAssessmentIds] = useState<string[]>([]);
  const [latestReport, setLatestReport] = useState<Diagnostic | null>(null);
  const [initialDraft, setInitialDraft] = useState("");
  const [partsDraft, setPartsDraft] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [composerVersion, setComposerVersion] = useState(0);
  const [pendingText, setPendingText] = useState("");
  const [history, setHistory] = useState<HistoryEntry[]>(() =>
    demo ? [] : readHistory(),
  );
  const [historyWarning, setHistoryWarning] = useState(false);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [currentUrgency, setCurrentUrgency] = useState<VehicleUrgency | null>(
    null,
  );
  const [caseLoading, setCaseLoading] = useState(false);
  const [caseError, setCaseError] = useState("");
  const caseRequest = useRef(0);
  const refreshCases = useCallback(
    async (vehicleId: string) => {
      const request = ++caseRequest.current;
      setCaseLoading(true);
      try {
        const snapshot = await api.caseHistory(vehicleId);
        if (request !== caseRequest.current) return false;
        if (snapshot.vehicle_urgency.vehicle_id !== vehicleId)
          throw new ApiError("Case history belongs to another vehicle.");
        setCases(snapshot.cases);
        setCurrentUrgency(snapshot.vehicle_urgency);
        setHistory(
          snapshot.cases.map((item) => ({
            conversationId: item.conversation_id,
            vehicleId: item.vehicle_id,
            createdAt: item.created_at,
          })),
        );
        setCaseError("");
        return true;
      } catch (e) {
        if (request === caseRequest.current) setCaseError(errorText(e));
        return false;
      } finally {
        if (request === caseRequest.current) setCaseLoading(false);
      }
    },
    [api],
  );
  useEffect(() => {
    setCases([]);
    setCurrentUrgency(null);
    setCaseLoading(false);
    setCaseError("");
    if (vehicle) void refreshCases(vehicle.vehicle_id);
    return () => {
      ++caseRequest.current;
    };
  }, [vehicle?.vehicle_id, refreshCases, retry]);
  useEffect(() => {
    const refresh = () => {
      if (vehicle && !busy) void refreshCases(vehicle.vehicle_id);
    };
    window.addEventListener("focus", refresh);
    return () => window.removeEventListener("focus", refresh);
  }, [vehicle?.vehicle_id, busy, refreshCases]);
  async function changeResolution(
    item: CaseSummary,
    resolve: boolean,
    note?: string,
  ) {
    if (!vehicle || busy) return false;
    setBusy(true);
    setCaseError("");
    try {
      const version = {
        expected_latest_diagnostic_id: item.latest_diagnostic_id,
      };
      if (resolve)
        await api.resolveCase(item.conversation_id, {
          ...version,
          resolution_note: note || null,
        });
      else await api.reopenCase(item.conversation_id, version);
      // Invalidate the shared history/urgency snapshot after every successful write.
      const refreshed = await refreshCases(vehicle.vehicle_id);
      if (!refreshed)
        setCaseError(
          "Case status was saved, but the history could not be refreshed. Refresh before making another change.",
        );
      return true;
    } catch (e) {
      await refreshCases(vehicle.vehicle_id);
      setCaseError(errorText(e));
      return false;
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    const resize = () => setIsMobile(window.innerWidth <= 1100);
    const update = () => {
      setView(viewFromHash());
      setMobileMenu(false);
      document.getElementById("main-content")?.focus({ preventScroll: true });
      window.scrollTo(0, 0);
    };
    window.addEventListener("resize", resize);
    window.addEventListener("hashchange", update);
    return () => {
      window.removeEventListener("resize", resize);
      window.removeEventListener("hashchange", update);
    };
  }, []);
  useEffect(() => {
    if (!mobileMenu || !isMobile) return;
    document
      .querySelector<HTMLElement>('.sidebar [aria-current="page"]')
      ?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMobileMenu(false);
        requestAnimationFrame(() =>
          document
            .querySelector<HTMLElement>('[aria-label="Open navigation"]')
            ?.focus(),
        );
      }
      if (event.key === "Tab") {
        const items = Array.from(
          document.querySelectorAll<HTMLElement>(
            ".sidebar a, .sidebar button:not(:disabled)",
          ),
        );
        const first = items[0],
          last = items.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        }
        if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", keydown);
    return () => document.removeEventListener("keydown", keydown);
  }, [mobileMenu, isMobile]);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setConnectionError("");
    void Promise.allSettled([api.health(), api.vehicles(), api.tools()]).then(
      ([h, v, t]) => {
        if (!active) return;
        if (h.status === "fulfilled") setHealth(h.value);
        else setHealth(null);
        if (v.status === "fulfilled")
          setVehicle(
            v.value.find(
              (item) =>
                item.manufacturer.toLowerCase() === "volkswagen" &&
                item.model.toLowerCase() === "golf plus" &&
                item.engine.toLowerCase() === "2.0 tdi",
            ) || null,
          );
        else setVehicle(null);
        setTools(t.status === "fulfilled" ? t.value : null);
        if (v.status === "rejected") setConnectionError(errorText(v.reason));
        else if (!v.value.length)
          setConnectionError("No vehicle is configured on the backend.");
        else if (h.status === "rejected")
          setConnectionError(errorText(h.reason));
        setLoading(false);
      },
    );
    return () => {
      active = false;
    };
  }, [api, retry]);
  const connected = !!vehicle && !!health && !connectionError;
  const displayVehicle = vehicle || demoVehicle;
  function navigate(next: View) {
    window.location.hash = next;
    setView(next);
    setMobileMenu(false);
  }
  function remember(entry: HistoryEntry) {
    const next = [
      entry,
      ...history.filter((item) => item.conversationId !== entry.conversationId),
    ].slice(0, 50);
    setHistory(next);
    if (!demo && !writeHistory(next)) setHistoryWarning(true);
  }
  function startNew(draft = "") {
    if (busy) return;
    setInitialDraft(draft);
    setThread([]);
    setReport(null);
    setAssessmentIds([]);
    setConversationId(null);
    setError(null);
    setComposerVersion((v) => v + 1);
    navigate("diagnostico");
  }
  async function send(observation: Observation) {
    if (!vehicle || busy) return false;
    setBusy(true);
    setPendingText(observation.description);
    setError(null);
    try {
      const result = conversationId
        ? await api.message(conversationId, observation)
        : await api.diagnose(vehicle.vehicle_id, observation);
      if (
        result.vehicle_id !== vehicle.vehicle_id ||
        (conversationId && result.conversation_id !== conversationId)
      )
        throw new ApiError(
          "The report does not belong to this consultation.",
          "invalid_response",
        );
      setReport(result);
      setAssessmentIds((ids) => [...ids, result.diagnostic_id]);
      setLatestReport(result);
      setConversationId(result.conversation_id);
      setThread((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "user",
          text: observation.description,
          codes: observation.dtcs,
        },
        { id: result.diagnostic_id, role: "assistant", text: result.summary },
      ]);
      remember({
        conversationId: result.conversation_id,
        vehicleId: result.vehicle_id,
        createdAt: result.created_at,
      });
      await refreshCases(vehicle.vehicle_id);
      return true;
    } catch (e) {
      setError(e);
      return false;
    } finally {
      setBusy(false);
      setPendingText("");
    }
  }
  async function openConversation(entry: HistoryEntry) {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const conversation = await api.conversation(entry.conversationId);
      if (conversation.vehicle_id !== vehicle?.vehicle_id)
        throw new ApiError("This consultation belongs to another vehicle.");
      const latest = conversation.diagnostic_ids?.at(-1);
      const lastReport = latest ? await api.diagnostic(latest) : null;
      const messages: ThreadMessage[] = (conversation.messages || []).map(
        (message, index) => {
          let text = message.content;
          let codes: string[] = [];
          if (message.role === "user") {
            try {
              const data = JSON.parse(text);
              if (typeof data.description === "string") text = data.description;
              if (Array.isArray(data.dtcs))
                codes = data.dtcs.filter((x: unknown) => typeof x === "string");
            } catch {
              /* Older messages can be plain text. */
            }
          }
          return {
            id: message.message_id || String(index),
            role: message.role,
            text,
            codes,
          };
        },
      );
      setConversationId(conversation.conversation_id);
      setThread(messages);
      setReport(lastReport);
      setAssessmentIds(conversation.diagnostic_ids || []);
      setLatestReport(lastReport);
      setInitialDraft("");
      setComposerVersion((v) => v + 1);
      navigate("diagnostico");
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function openAssessment(id: string) {
    if (busy || !assessmentIds.includes(id)) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.diagnostic(id);
      if (
        result.conversation_id !== conversationId ||
        result.vehicle_id !== vehicle?.vehicle_id
      )
        throw new ApiError("This assessment belongs to another case.");
      setReport(result);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className={`app-shell ${view === "inicio" ? "is-home" : ""}`}>
      <a
        href="#main-content"
        className="skip-link"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById("main-content")?.focus();
        }}
      >
        Skip to content{" "}
      </a>
      {mobileMenu && (
        <button
          className="sidebar-scrim"
          aria-label="Close navigation"
          onClick={() => setMobileMenu(false)}
        />
      )}
      <aside
        className={`sidebar ${mobileMenu ? "is-open" : ""}`}
        aria-label="Main menu"
        inert={isMobile && !mobileMenu}
        aria-hidden={isMobile && !mobileMenu ? true : undefined}
      >
        <button
          className="icon-button mobile-close"
          onClick={() => {
            setMobileMenu(false);
            requestAnimationFrame(() =>
              document
                .querySelector<HTMLElement>('[aria-label="Open navigation"]')
                ?.focus(),
            );
          }}
          aria-label="Close menu"
        >
          <X size={20} />
        </button>
        <a className="brand" href="#inicio" aria-label="Motor, home">
          <span className="brand-symbol">
            <CarFront size={43} strokeWidth={1.4} aria-hidden="true" />
          </span>
          <span>
            motor<span className="brand-dot">.</span>
            <small>Diagnostic assistant</small>
          </span>
        </a>
        <nav aria-label="Sections">
          {navigation.map((item) => (
            <span className="nav-item" key={item.key}>
              <a
                href={`#${item.key}`}
                aria-current={view === item.key ? "page" : undefined}
                aria-disabled={busy}
                onClick={(e) => {
                  if (busy) e.preventDefault();
                }}
              >
                <item.icon size={20} aria-hidden="true" />
                {item.label}
              </a>
              {item.key === "inicio" && (
                <button
                  className="nav-new"
                  aria-label="Create a new diagnosis"
                  aria-current={view === "diagnostico" ? "page" : undefined}
                  onClick={() => startNew()}
                  disabled={busy}
                >
                  <Plus size={21} aria-hidden="true" />
                  New Diagnosis{" "}
                </button>
              )}
            </span>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <nav aria-label="Utilities">
            <a
              href="#configuracion"
              aria-current={view === "configuracion" ? "page" : undefined}
            >
              <Settings2 size={20} aria-hidden="true" />
              Settings{" "}
            </a>
            <a
              href="#ayuda"
              aria-current={view === "ayuda" ? "page" : undefined}
            >
              <CircleHelp size={20} aria-hidden="true" />
              Help{" "}
            </a>
          </nav>
          <div className="sidebar-vehicle">
            <span className="sidebar-mini-icon">
              <CarFront size={38} strokeWidth={1.3} aria-hidden="true" />
            </span>
            <div>
              <strong>
                Volkswagen
                <br />
                Golf Plus
              </strong>
              <small>
                {vehicle
                  ? `${vehicle.model_year} · ${vehicle.engine}`
                  : "Loading vehicle…"}
              </small>
            </div>
            <button
              aria-label="View my vehicle"
              onClick={() => navigate("vehiculo")}
              disabled={busy}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </aside>
      <div className="main-shell" inert={isMobile && mobileMenu}>
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            onClick={() => setMobileMenu(true)}
            aria-label="Open navigation"
          >
            <Menu size={21} />
          </button>
          <div className="breadcrumb">
            Your workspace <ChevronRight size={13} aria-hidden="true" />
            <strong>{viewLabels[view]}</strong>
          </div>
          <div className="topbar-right">
            <span className="topbar-vehicle">
              <CarFront size={15} aria-hidden="true" />
              Volkswagen Golf Plus
              <span className="topbar-divider" />
              {vehicle?.model_year ?? "—"}
            </span>
            {demo ? (
              <details className="demo-indicator">
                <summary>
                  <FlaskConical size={18} aria-hidden="true" />
                  <span>Demo mode</span>
                  <Info size={15} aria-hidden="true" />
                </summary>
                <div className="demo-popover">
                  <strong>Interface demonstration</strong>
                  <p>
                    Synthetic data held in memory. No AI, PostgreSQL,
                    documentation or live providers are consulted. Examples
                    disappear on reload.{" "}
                  </p>
                  <a
                    href={modeLink(false)}
                    onClick={(e) => {
                      if (busy) e.preventDefault();
                    }}
                  >
                    Exit demo <ArrowUpRight size={14} />
                  </a>
                </div>
              </details>
            ) : (
              <span
                className={`connection-state ${connected ? "connected" : ""}`}
                role="status"
              >
                <span className={`status-dot ${connected ? "ready" : ""}`} />
                {loading
                  ? "Connecting"
                  : connected
                    ? "Backend connected"
                    : "Offline"}
              </span>
            )}
          </div>
        </header>
        <main id="main-content" className="main-content" tabIndex={-1}>
          {view !== "inicio" && (
            <div className="page-heading">
              <div>
                <div className="eyebrow">
                  <span className="tiny-line" />
                  YOUR VEHICLE, IN CONTEXT.{" "}
                </div>
                <h1>
                  {
                    {
                      diagnostico: "Let us talk about your car.",
                      informe: "Your guidance, in detail.",
                      evidencia: "Technical evidence.",
                      vehiculo: "Every detail helps.",
                      recambios: "Search with context.",
                      historial: "Resume the conversation.",
                      configuracion: "Your workspace settings.",
                      ayuda: "A little clarity.",
                    }[view]
                  }
                </h1>
                <p>
                  {
                    {
                      diagnostico:
                        "A conversation to organize symptoms, assess urgency and decide what to do next.",
                      informe:
                        "Symptoms, hypotheses, checks and sources, without treating a fault as confirmed.",
                      evidencia:
                        "Available sources for this consultation, including provenance and limitations.",
                      vehiculo:
                        "Only known details. Unknown information is not assumed.",
                      recambios:
                        "Candidates, compatibility and prices, with clear provenance.",
                      historial:
                        "Track active and resolved cases without changing their original assessments.",
                      configuracion:
                        "Review service status and the current operating mode.",
                      ayuda:
                        "How to use Motor and understand the limits of its guidance.",
                    }[view]
                  }
                </p>
              </div>
              <span className="page-corner-mark">
                <Wrench size={22} strokeWidth={1.3} />
                OBSERVE.
                <br />
                UNDERSTAND.
              </span>
            </div>
          )}
          {loading && (
            <div className="connection-loading">
              <Spinner label="Checking services and vehicle…" />
            </div>
          )}
          {!loading && connectionError && (
            <div className="connection-notice">
              <div>
                <strong>Backend unavailable</strong>
                <p>{connectionError}</p>
              </div>
              <button
                className="button secondary"
                onClick={() => setRetry((v) => v + 1)}
              >
                <RotateCw size={15} aria-hidden="true" />
                Retry{" "}
              </button>
              <a className="button text-button" href={modeLink(true)}>
                Explore demo <ArrowRight size={15} aria-hidden="true" />
              </a>
            </div>
          )}
          {!!error && (
            <ErrorNotice
              text={errorText(error)}
              requestId={
                error instanceof ApiError ? error.requestId : undefined
              }
            />
          )}
          {historyWarning && (
            <p className="storage-warning" role="status">
              This browser cannot save the consultation link. The report remains
              in the backend.{" "}
            </p>
          )}
          {view === "inicio" && (
            <HomePage
              vehicle={displayVehicle}
              report={latestReport}
              currentUrgency={currentUrgency}
              busy={busy}
              onStart={startNew}
              history={history}
              connected={connected}
              onOpen={(entry) => void openConversation(entry)}
              onSources={() => navigate("evidencia")}
              onParts={() => navigate("recambios")}
              onComponentParts={(component) => {
                setPartsDraft(component);
                navigate("recambios");
              }}
              onVehicle={() => navigate("vehiculo")}
            />
          )}
          {(view === "informe" || view === "evidencia") && (
            <div className="full-report">
              <AssessmentSelector
                ids={assessmentIds}
                selected={report?.diagnostic_id}
                disabled={busy}
                onSelect={(id) => void openAssessment(id)}
              />
              <div className="report-page-actions">
                <span className="eyebrow">
                  {vehicle
                    ? `${vehicle.model} · ${vehicle.model_year} · ${vehicle.engine}`
                    : "Vehicle documentation"}
                </span>
                <button
                  className="button secondary"
                  onClick={() => navigate("diagnostico")}
                >
                  Back to conversation <ArrowRight size={17} />
                </button>
              </div>
              <Report
                key={view}
                report={report || latestReport}
                demo={demo}
                expanded={view === "informe"}
                initialTab={view === "evidencia" ? "fuentes" : "resumen"}
              />
            </div>
          )}
          {view === "diagnostico" && (
            <>
              <section
                className="vehicle-strip"
                aria-label="Consultation vehicle"
              >
                <div className="vehicle-strip-illustration">
                  <CarIllustration />
                  <AssetCredits compact={false} />
                </div>
                <div className="vehicle-strip-name">
                  <span className="eyebrow">
                    {connected ? "SELECTED VEHICLE" : "MVP VEHICLE"}
                  </span>
                  <h2>
                    {displayVehicle.manufacturer} {displayVehicle.model}
                    <span>{displayVehicle.model_year}</span>
                  </h2>
                  <p>
                    {displayVehicle.engine} <span>·</span> Diesel <span>·</span>{" "}
                    Manual
                  </p>
                </div>
                <div className="vehicle-strip-detail">
                  <small>Engine code</small>
                  <span>
                    {displayVehicle.engine_code || "Not specified"}
                    {!displayVehicle.engine_code && (
                      <CircleHelp size={13} aria-hidden="true" />
                    )}
                  </span>
                </div>
                <button
                  className="button text-button"
                  onClick={() => navigate("vehiculo")}
                  disabled={!vehicle || busy}
                >
                  View vehicle <ArrowUpRight size={15} aria-hidden="true" />
                </button>
              </section>
              <div className="diagnostic-workspace">
                <section
                  className="panel conversation-panel"
                  aria-label="Diagnostic conversation"
                >
                  <header className="panel-header">
                    <span className="panel-icon">
                      <MessageSquare size={18} aria-hidden="true" />
                    </span>
                    <h2>Let us discuss the symptoms</h2>
                    <Badge>
                      {conversationId
                        ? "Consultation in progress"
                        : "New consultation"}
                    </Badge>
                  </header>
                  <div
                    className="conversation-thread"
                    aria-live="polite"
                    aria-relevant="additions"
                  >
                    {!thread.length && (
                      <div className="welcome-message">
                        <div className="assistant-avatar">
                          <Activity size={21} aria-hidden="true" />
                        </div>
                        <span className="assistant-label">
                          MOTOR <span>·</span> YOUR ASSISTANT{" "}
                        </span>
                        <h3>Hello. Let us start with what you notice.</h3>
                        <p>
                          You do not need mechanical expertise. Describe the
                          problem in your own words:{" "}
                        </p>
                        <ul>
                          <li>What happens, and when did it start?</li>
                          <li>When cold, when warm or while driving?</li>
                          <li>Any new warning lights, noises or behavior? </li>
                        </ul>
                        <p className="welcome-closure">
                          Describe what you observe without assuming a
                          fault.{" "}
                        </p>
                      </div>
                    )}
                    {thread.map((message) => (
                      <article
                        className={`chat-message ${message.role}`}
                        key={message.id}
                      >
                        <span className="chat-role">
                          {message.role === "user" ? "You" : "Motor · Guidance"}
                        </span>
                        <p>{message.text}</p>
                        {!!message.codes?.length && (
                          <div className="code-list">
                            {message.codes.map((code, i) => (
                              <Badge key={i}>{code}</Badge>
                            ))}
                          </div>
                        )}
                      </article>
                    ))}
                    {pendingText && (
                      <article className="chat-message user pending">
                        <span className="chat-role">You · Sending</span>
                        <p>{pendingText}</p>
                      </article>
                    )}
                    {busy && pendingText && (
                      <div className="thinking">
                        <Spinner
                          label={
                            demo
                              ? "Preparing the example…"
                              : "Organizing symptoms and checking safety…"
                          }
                        />
                      </div>
                    )}
                  </div>
                  <Composer
                    key={composerVersion}
                    onSend={send}
                    busy={busy}
                    disabled={!connected || loading}
                    hasMessages={!!thread.length}
                    initialText={initialDraft}
                  />
                </section>
                <div className="workspace-report">
                  <AssessmentSelector
                    ids={assessmentIds}
                    selected={report?.diagnostic_id}
                    disabled={busy}
                    onSelect={(id) => void openAssessment(id)}
                  />
                  <Report report={report} demo={demo} />
                  {report && (
                    <button
                      className="button secondary full-report-link"
                      disabled={busy}
                      onClick={() => navigate("informe")}
                    >
                      <FileText size={16} />
                      Open full report <ArrowUpRight size={16} />
                    </button>
                  )}
                </div>
              </div>
              <div className="service-notes">
                <span>
                  <BookOpen size={14} aria-hidden="true" />
                  {report?.citations?.length
                    ? "Review provenance under Sources and limits"
                    : "No manufacturer documentation retrieved"}
                </span>
                <span>
                  <PackageSearch size={14} aria-hidden="true" />
                  {tools?.demo_data
                    ? "Demo catalog · no real commercial data"
                    : "No verified commercial provider"}
                </span>
              </div>
            </>
          )}
          {view === "vehiculo" && vehicle && (
            <VehiclePage
              key={vehicle.vehicle_id}
              vehicle={vehicle}
              api={api}
              onSave={setVehicle}
              demo={demo}
            />
          )}
          {view === "recambios" && vehicle && (
            <PartsPage
              api={api}
              vehicle={vehicle}
              initialComponent={partsDraft}
            />
          )}
          {["vehiculo", "recambios"].includes(view) && !vehicle && !loading && (
            <div className="panel disconnected-placeholder">
              <CarFront size={36} aria-hidden="true" />
              <h2>Connect to your vehicle first.</h2>
              <p>Start the backend or explore the demo examples.</p>
              <a className="button primary" href={modeLink(true)}>
                Explore demo <ArrowRight size={16} />
              </a>
            </div>
          )}
          {view === "historial" && (
            <HistoryPage
              cases={cases}
              busy={busy || !connected}
              loading={caseLoading}
              error={caseError}
              demo={demo}
              onOpen={(entry) => void openConversation(entry)}
              onChange={changeResolution}
              onRefresh={() => {
                if (vehicle) void refreshCases(vehicle.vehicle_id);
              }}
            />
          )}
          {view === "inicio" && caseError && (
            <p className="storage-warning" role="alert">
              Current case status could not be refreshed: {caseError} The last
              available assessment may be shown.
              <button
                className="button text-button"
                disabled={busy || caseLoading}
                onClick={() => {
                  if (vehicle) void refreshCases(vehicle.vehicle_id);
                }}
              >
                Refresh cases
              </button>
            </p>
          )}
          {view === "configuracion" && (
            <section className="panel utility-panel">
              <div className="panel-header">
                <Settings2 size={21} />
                <h2>Service status</h2>
              </div>
              <div className="panel-body">
                <dl className="service-grid">
                  {[
                    [
                      "Operating mode",
                      demo ? "Explicit demo · synthetic data" : "Live backend",
                    ],
                    [
                      "Connection",
                      loading
                        ? "Checking…"
                        : connected
                          ? "Available"
                          : "Offline",
                    ],
                    [
                      "Persistence",
                      demo
                        ? "Temporary demo memory"
                        : health?.persistence || "No information",
                    ],
                    [
                      "AI model",
                      demo
                        ? "Not used in demo mode"
                        : health?.llm_configured
                          ? "Configured"
                          : "Not configured or no information",
                    ],
                    [
                      "RAG documentation",
                      demo
                        ? "Not queried in demo mode"
                        : health?.rag_available
                          ? "Available according to backend"
                          : "Unavailable",
                    ],
                    [
                      "MCP tools",
                      demo
                        ? "Simulated examples"
                        : health?.mcp_available
                          ? "Available according to backend"
                          : "Unavailable",
                    ],
                  ].map(([label, value]) => (
                    <div key={label}>
                      <dt>{label}</dt>
                      <dd>{value}</dd>
                    </div>
                  ))}
                </dl>
                <button
                  className="button secondary"
                  onClick={() => setRetry((v) => v + 1)}
                >
                  <RotateCw size={16} />
                  Check connection{" "}
                </button>
                <p className="muted">
                  Credentials and providers are configured on the server. The
                  browser does not store API keys.{" "}
                </p>
                <a className="source-link" href={modeLink(!demo)}>
                  {demo
                    ? "Return to live backend"
                    : "Explore the explicit demo"}
                  <ArrowUpRight size={15} />
                </a>
                <section
                  className="settings-asset-credits"
                  aria-labelledby="settings-asset-credits-title"
                >
                  <h2 id="settings-asset-credits-title">Asset Credits</h2>
                  <AssetCreditsContent />
                </section>
              </div>
            </section>
          )}
          {view === "ayuda" && (
            <section className="panel utility-panel">
              <div className="panel-header">
                <CircleHelp size={21} />
                <h2>Understand before repairing</h2>
              </div>
              <div className="panel-body help-content">
                <h3>Start with what you observe</h3>
                <p>
                  Start a consultation and describe what happens, when it
                  started and under which conditions. Add OBD codes and warning
                  lights if known; leave unknown information blank.{" "}
                </p>
                <h3>Read urgency before hypotheses</h3>
                <p>
                  The report separates symptoms, possible causes and checks. Add
                  details in the conversation. A hypothesis requires
                  verification; it does not confirm a fault or a need to buy
                  parts.{" "}
                </p>
                <h3>Check provenance</h3>
                <p>
                  Demo references, general knowledge and tool results have
                  distinct labels. A parts candidate does not prove
                  compatibility. Without sufficient evidence, compatibility
                  remains unknown.{" "}
                </p>
                <h3>Retrieve a consultation</h3>
                <p>
                  History and resolution status come from the backend. Resolved
                  cases retain their reports and can be reopened. Demo examples
                  are temporary and disappear on reload.{" "}
                </p>
                <button className="button primary" onClick={() => startNew()}>
                  Create a consultation <ArrowRight size={17} />
                </button>
              </div>
            </section>
          )}
          {view !== "inicio" && (
            <aside className="safety-guide" id="safety-guide">
              <ShieldCheck size={21} aria-hidden="true" />
              <div>
                <strong>Your safety comes before any hypothesis.</strong>
                <p>
                  If brakes or steering fail, or there is smoke, fire or a major
                  leak, stop safely, do not continue driving and seek
                  assistance.{" "}
                </p>
              </div>
            </aside>
          )}
          <footer className="page-footer">
            <span>Motor · Diagnostic Assistant</span>
            <span>Guidance, never a confirmed repair.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
