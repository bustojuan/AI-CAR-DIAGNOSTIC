import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { sampleReport } from "../demo/api";
import { Report } from "./Report";

it("shows backend urgency explanation, warnings, gaps and recommendations", () => {
  const report = sampleReport(crypto.randomUUID(), true);
  render(<Report report={report} />);
  expect(screen.getByRole("alert")).toHaveTextContent("Stop safely");
  expect(
    screen.getByText(report.urgency_assessment!.explanation),
  ).toBeVisible();
  expect(screen.getByText("Example possible loss of braking")).toBeVisible();
  expect(
    screen.getByRole("heading", { name: "Missing safety information" }),
  ).toBeVisible();
  expect(
    screen.getByText("Professional assistance recommended:"),
  ).toBeVisible();
  expect(screen.getByText("Yes")).toBeVisible();
});

it("does not invent missing details for a historical report", () => {
  const report = {
    ...sampleReport(crypto.randomUUID()),
    urgency_assessment: null,
  };
  render(<Report report={report} />);
  expect(
    screen.getByText(/Additional urgency details were not recorded/),
  ).toBeVisible();
});
