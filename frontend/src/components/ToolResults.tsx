import {
  CircleHelp,
  FlaskConical,
  PackageSearch,
  ShieldQuestion,
} from "lucide-react";
import type { ToolResult } from "../api/types";
import { dateLabel } from "../lib/history";
import { Badge, SourceLink } from "./ui";

const titles = {
  search_parts: "Candidates found",
  check_compatibility: "Compatibility check",
  get_part_prices: "Price query",
};
const compatibility = {
  unknown: "Compatibility unknown",
  requires_additional_information: "More information needed to verify",
  confirmed_compatible: "Compatible according to provider evidence",
  confirmed_incompatible: "Incompatible according to provider evidence",
};
function money(amount: string, currency: string) {
  try {
    return new Intl.NumberFormat("en-GB", {
      style: "currency",
      currency,
    }).format(Number(amount));
  } catch {
    return `${amount} ${currency}`;
  }
}
export function ToolResults({ results }: { results: ToolResult[] }) {
  return (
    <div className="tool-results">
      {results.map((result, index) => {
        const demo =
          result.demo_data ||
          result.verification === "synthetic" ||
          result.provider === "demo";
        const fitment =
          !demo &&
          result.verification === "verified_provider" &&
          (result.evidence?.length || 0) > 0
            ? result.compatibility
            : "unknown";
        return (
          <section className="tool-result" key={result.execution_id || index}>
            <div className="section-heading">
              <h3>{titles[result.tool]}</h3>
              <Badge tone={demo ? "amber" : "neutral"}>
                {demo
                  ? result.provider === "ebay_sandbox"
                    ? "eBay Sandbox · test data"
                    : "Synthetic data"
                  : result.available
                    ? "Provider data"
                    : "Unavailable"}
              </Badge>
            </div>
            {demo && (
              <p className="demo-explanation">
                <FlaskConical size={15} aria-hidden="true" />
                Demonstration: products, prices and compatibility are not
                real.{" "}
              </p>
            )}
            {!result.available && (
              <div className="unavailable-result">
                <CircleHelp size={20} aria-hidden="true" />
                <p>{result.reason}</p>
              </div>
            )}
            {result.available && result.tool === "search_parts" && (
              <>
                {!result.parts?.length && (
                  <p className="muted">No candidates found for this query. </p>
                )}
                {result.parts?.map((part) => (
                  <div className="part-result" key={part.part_id}>
                    <div className="part-icon">
                      <PackageSearch size={21} aria-hidden="true" />
                    </div>
                    <div>
                      <h4>{part.name}</h4>
                      <p>
                        {part.manufacturer} · {part.brand}
                      </p>
                      <span className="mono">{part.part_id}</span>
                      <p className="part-description">{part.description}</p>
                      <Badge>Compatibility unconfirmed</Badge>
                      {part.oem_reference && part.oem_verified && !demo && (
                        <p>Verified OEM reference: {part.oem_reference}</p>
                      )}
                      <SourceLink url={part.source_url} />
                    </div>
                  </div>
                ))}
                <p className="fine-print">
                  A candidate does not confirm the cause of a fault or a need to
                  replace a part.{" "}
                </p>
              </>
            )}
            {result.available && result.tool === "check_compatibility" && (
              <div className="fitment-result">
                <ShieldQuestion size={24} aria-hidden="true" />
                <div>
                  <h4>{compatibility[fitment]}</h4>
                  <p>Reference: {result.part_id || "Not supplied"}</p>
                  {result.missing_information?.includes("engine_code") && (
                    <p>
                      The engine code is missing. Add it in My Vehicle. Do not
                      share the VIN.{" "}
                    </p>
                  )}
                  {result.evidence?.map((text, i) => (
                    <p key={i}>{text}</p>
                  ))}
                </div>
              </div>
            )}
            {result.available && result.tool === "get_part_prices" && (
              <>
                {(result.provider === "ebay" ||
                  result.provider === "ebay_sandbox") && (
                  <p className="fine-print">{result.reason}</p>
                )}
                {!result.prices?.length && (
                  <p className="muted">
                    No verified prices are available for this reference.{" "}
                  </p>
                )}
                {result.prices?.map((price, i) => (
                  <div className="price-result" key={i}>
                    <div>
                      <h4>{price.merchant}</h4>
                      <p>
                        {price.part_id} · {price.country} · {price.quantity}{" "}
                        {result.provider === "ebay"
                          ? "listing(s)"
                          : "unit(s)"}{" "}
                      </p>
                      <p>
                        {price.tax_included === true
                          ? "Tax included"
                          : price.tax_included === false
                            ? "Tax excluded"
                            : "Tax unconfirmed"}
                      </p>
                    </div>
                    <div className="price-amount">
                      <strong>{money(price.unit_price, price.currency)}</strong>
                      <small>
                        {result.provider === "ebay"
                          ? "per listing/lot"
                          : "per unit"}{" "}
                        ·{" "}
                        {demo || price.verification === "synthetic"
                          ? "synthetic price"
                          : price.verification === "historical"
                            ? "historical price"
                            : "price retrieved from provider"}
                      </small>
                    </div>
                    <p className="fine-print">
                      Availability:{" "}
                      {demo || price.availability === "demonstration"
                        ? "simulated"
                        : price.availability === "in_stock"
                          ? "in stock according to provider"
                          : price.availability === "out_of_stock"
                            ? "out of stock according to provider"
                            : "unconfirmed"}
                      .{" "}
                      {price.retrieved_at
                        ? dateLabel(price.retrieved_at)
                        : "Date not supplied"}
                      .
                    </p>
                    <SourceLink url={price.product_url} label="View product" />
                  </div>
                ))}
              </>
            )}
            <details className="provenance">
              <summary>Data provenance and status</summary>
              <p>{result.reason}</p>
              <p>
                Provider: {result.provider} ·{" "}
                {result.retrieved_at
                  ? dateLabel(result.retrieved_at)
                  : "No date"}
              </p>
              <p className="mono">{result.execution_id}</p>
            </details>
          </section>
        );
      })}
    </div>
  );
}
