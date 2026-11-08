import type { ReactNode, KeyboardEvent } from "react";
import { AlertCircle, ArrowUpRight, LoaderCircle } from "lucide-react";
import { safeLink } from "../lib/history";
import { vehicleIllustration } from "./vehicle3d/illustration";

export function navigateTabs(event: KeyboardEvent<HTMLDivElement>) {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
  const tabs = Array.from(
    event.currentTarget.querySelectorAll<HTMLButtonElement>(
      '[role="tab"]:not(:disabled)',
    ),
  );
  const current = tabs.indexOf(document.activeElement as HTMLButtonElement);
  const next =
    event.key === "Home"
      ? 0
      : event.key === "End"
        ? tabs.length - 1
        : (current + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) %
          tabs.length;
  event.preventDefault();
  tabs[next]?.focus();
  tabs[next]?.click();
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
export function ErrorNotice({
  text,
  requestId,
}: {
  text: string;
  requestId?: string;
}) {
  return (
    <div className="error-notice" role="alert">
      <AlertCircle size={18} aria-hidden="true" />
      <div>
        {text}
        {requestId && <small>Reference: {requestId}</small>}
      </div>
    </div>
  );
}
export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <span className="loading" role="status">
      <LoaderCircle size={17} className="spin" aria-hidden="true" />
      {label}
    </span>
  );
}
export function SourceLink({
  url,
  label = "View source",
}: {
  url?: string | null;
  label?: string;
}) {
  const href = safeLink(url);
  return href ? (
    <a
      className="source-link"
      href={href}
      target="_blank"
      rel="noopener noreferrer"
    >
      {label}
      <ArrowUpRight size={14} aria-hidden="true" />
    </a>
  ) : null;
}
export function CarIllustration({
  alt = vehicleIllustration.alt,
  src = vehicleIllustration.src,
}: { alt?: string; src?: string } = {}) {
  return (
    <img
      className="car-illustration"
      src={src}
      alt={alt}
      width="1200"
      height="675"
      draggable={false}
    />
  );
}
