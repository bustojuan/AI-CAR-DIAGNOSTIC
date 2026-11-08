import {
  Activity,
  ArrowRight,
  Clock3,
  Cloud,
  Engine,
  FileText,
  Fuel,
  Gauge,
  Layers,
  MessageSquare,
  Package,
  Plus,
  Settings2,
  Signal,
  Thermometer,
  TriangleAlert,
  Volume2,
  Wrench,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type {
  Diagnostic,
  HistoryEntry,
  Vehicle,
  VehicleUrgency,
} from "../api/types";
import { Vehicle3DViewer } from "./Vehicle3DViewer";
import { dashboardVehicleModel, golfPlusEngineBay } from "./vehicle3d/asset";
import { dateLabel } from "../lib/history";
import { UrgencyGuide } from "./UrgencyGuide";

const urgencyLabels = {
  low: "Low",
  moderate: "Moderate",
  high: "High",
  critical: "Critical",
};
const symptoms: {
  label: string;
  description: string;
  icon: LucideIcon;
  warning?: boolean;
}[] = [
  {
    label: "Starting problems",
    description: "My car has difficulty starting. ",
    icon: Wrench,
  },
  {
    label: "Engine warning light",
    description: "The engine warning light has come on. ",
    icon: Engine,
    warning: true,
  },
  {
    label: "Loss of power",
    description: "I have noticed a loss of power in my car. ",
    icon: Signal,
  },
  {
    label: "Unusual noises",
    description: "I hear an unusual noise in my car. ",
    icon: Volume2,
  },
  {
    label: "Overheating",
    description:
      "I have noticed that the engine temperature rises above normal. ",
    icon: Thermometer,
  },
  {
    label: "Excessive smoke",
    description: "I have noticed more smoke than usual from my car. ",
    icon: Cloud,
  },
];

function FeatureCard({
  title,
  description,
  icon: Icon,
  image,
  onClick,
  busy,
}: {
  title: string;
  description: string;
  icon: LucideIcon;
  image: string;
  onClick: () => void;
  busy: boolean;
}) {
  return (
    <button
      className={`feature-card feature-${image}`}
      onClick={onClick}
      disabled={busy}
    >
      <span className="feature-photo" aria-hidden="true" />
      <Icon
        className="feature-icon"
        size={32}
        strokeWidth={1.7}
        aria-hidden="true"
      />
      <span className="feature-copy">
        <strong>{title}</strong>
        <span>{description}</span>
      </span>
      <span className="round-arrow" aria-hidden="true">
        <ArrowRight size={22} />
      </span>
    </button>
  );
}

export function HomePage({
  vehicle,
  report,
  currentUrgency,
  history = [],
  connected = false,
  busy,
  onStart,
  onSources,
  onParts,
  onComponentParts,
  onVehicle,
  onOpen,
}: {
  vehicle: Vehicle;
  report: Diagnostic | null;
  currentUrgency?: VehicleUrgency | null;
  history?: HistoryEntry[];
  connected?: boolean;
  busy: boolean;
  onStart: (draft?: string) => void;
  onSources: () => void;
  onParts: () => void;
  onComponentParts?: (component: string) => void;
  onVehicle: () => void;
  onOpen: (entry: HistoryEntry) => void;
}) {
  const metrics = [
    {
      icon: Activity,
      label: "Overall status",
      value: currentUrgency
        ? currentUrgency.active_case_count
          ? "Active issues reported"
          : "No active issues reported"
        : "Awaiting assessment",
    },
    {
      icon: TriangleAlert,
      label: "Estimated urgency",
      value: currentUrgency?.urgency_level
        ? urgencyLabels[currentUrgency.urgency_level]
        : "Not assessed",
      warning: true,
    },
    {
      icon: FileText,
      label: "Available evidence",
      value: report?.citations?.length
        ? `${report.citations.length} references retrieved`
        : "No evidence retrieved",
    },
  ];
  return (
    <div className="home-page">
      <section className="home-hero" aria-labelledby="home-title">
        <div className="hero-copy">
          <div className="eyebrow">AUTOMOTIVE DIAGNOSTIC ASSISTANT</div>
          <h1 id="home-title">
            Understand your car <br />
            and the next step<span className="heading-dot">.</span>
          </h1>
          <p>
            Clear, practical diagnostic guidance. Tell us the symptoms; we
            review the information and help you decide what to do next.{" "}
          </p>
          <button
            className="button primary hero-cta"
            onClick={() => onStart()}
            disabled={busy}
          >
            <Plus size={23} strokeWidth={1.7} aria-hidden="true" />
            New Diagnosis <ArrowRight size={23} aria-hidden="true" />
          </button>
        </div>
        <div className="hero-vehicle">
          <div className="vehicle-light" />
          <div className="studio-floor" />
          <Vehicle3DViewer
            model={dashboardVehicleModel}
            explorer={{
              vehicle,
              engineBay: golfPlusEngineBay,
              onAskAI: busy ? undefined : onStart,
              onFindParts: busy ? undefined : onComponentParts,
            }}
          />
        </div>
        <button
          className="hero-specs"
          onClick={onVehicle}
          disabled={busy}
          aria-label="View Volkswagen Golf Plus details"
        >
          <h2>
            {vehicle.manufacturer} <br />
            {vehicle.model}
          </h2>
          <span className="model-year">{vehicle.model_year}</span>
          <span>
            <Engine size={20} strokeWidth={1.6} />
            {vehicle.engine}
          </span>
          <span>
            <Fuel size={20} strokeWidth={1.6} />
            Diesel{" "}
          </span>
          <span>
            <Settings2 size={20} strokeWidth={1.6} />
            Manual
          </span>
          <small>
            Engine code:{" "}
            <strong>{vehicle.engine_code || "Not specified"}</strong>
          </small>
        </button>
      </section>
      <section
        className="overview-status"
        aria-label="Latest consultation status"
        title={currentUrgency?.explanation}
      >
        {metrics.map((item) => (
          <div className="overview-metric" key={item.label}>
            {item.warning ? (
              <UrgencyGuide />
            ) : (
              <span className="metric-icon">
                <item.icon size={31} strokeWidth={1.7} aria-hidden="true" />
              </span>
            )}
            <div>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </div>
          </div>
        ))}
      </section>
      {currentUrgency?.urgency_level === "critical" && (
        <div className="urgency-banner critical" role="alert">
          <TriangleAlert size={23} aria-hidden="true" />
          <strong>
            Stop safely. Do not continue driving. Seek professional
            assistance.{" "}
          </strong>
        </div>
      )}
      <section className="home-features" aria-label="Explore your diagnosis">
        <FeatureCard
          title="Conversational diagnosis"
          description="Describe what you notice and we will ask questions to understand the problem."
          icon={MessageSquare}
          image="engine"
          onClick={() => onStart()}
          busy={busy}
        />
        <FeatureCard
          title="Technical Evidence"
          description="Review the technical documentation available for your vehicle."
          icon={Layers}
          image="manual"
          onClick={onSources}
          busy={busy}
        />
        <FeatureCard
          title="Parts and compatibility"
          description="Find components and review available compatibility and pricing information."
          icon={Package}
          image="brakes"
          onClick={onParts}
          busy={busy}
        />
      </section>
      <div className="dashboard-lower">
        <section
          className="dashboard-panel recent-panel"
          aria-labelledby="recent-title"
        >
          <header>
            <Clock3 size={24} aria-hidden="true" />
            <h2 id="recent-title">Recent activity</h2>
          </header>
          {!history.length ? (
            <div className="recent-empty">
              <FileText size={33} strokeWidth={1.6} aria-hidden="true" />
              <h3>No diagnoses yet</h3>
              <p>Your first consultation will appear here.</p>
            </div>
          ) : (
            <div className="recent-list">
              {history.slice(0, 3).map((entry, i) => (
                <button
                  onClick={() => onOpen(entry)}
                  disabled={busy || !connected}
                  key={entry.conversationId}
                  aria-label={`Resume diagnosis ${i + 1}`}
                >
                  <FileText size={22} aria-hidden="true" />
                  <span>
                    <strong>Consultation · Golf Plus</strong>
                    <small>{dateLabel(entry.createdAt)}</small>
                  </span>
                  <ArrowRight size={18} aria-hidden="true" />
                </button>
              ))}
            </div>
          )}
        </section>
        <section
          className="dashboard-panel symptoms-panel"
          aria-labelledby="symptoms-title"
        >
          <header>
            <Gauge size={24} aria-hidden="true" />
            <h2 id="symptoms-title">Common symptoms</h2>
          </header>
          <div className="symptom-grid">
            {symptoms.map((item) => (
              <button
                key={item.label}
                onClick={() => onStart(item.description)}
                disabled={busy}
              >
                <item.icon
                  size={25}
                  strokeWidth={1.7}
                  className={item.warning ? "warm" : ""}
                  aria-hidden="true"
                />
                <span>{item.label}</span>
              </button>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
