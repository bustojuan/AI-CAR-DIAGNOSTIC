import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { App } from "../App";
import { createDemoApi, sampleReport } from "../demo/api";
import { HomePage } from "./HomePage";
import { demoVehicle } from "../demo/api";

// These tests exercise diagnostic/navigation UI in jsdom. Real model loading and
// WebGL interaction are verified with the configured asset in Playwright.
vi.mock("./vehicle3d/asset", () => ({
  dashboardVehicleModel: null,
  golfPlusEngineBay: null,
}));

describe("overview and report navigation", () => {
  it("explains every urgency level from the status icon without running a diagnosis", async () => {
    const user = userEvent.setup();
    const onStart = vi.fn();
    render(
      <HomePage
        vehicle={demoVehicle}
        report={null}
        busy={false}
        onStart={onStart}
        onSources={vi.fn()}
        onOpen={vi.fn()}
        onParts={vi.fn()}
        onVehicle={vi.fn()}
      />,
    );
    const trigger = screen.getByRole("button", {
      name: "Explain estimated urgency levels",
    });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    trigger.focus();
    await user.keyboard("{Enter}");
    const dialog = screen.getByRole("dialog", {
      name: "Estimated urgency explained",
    });
    for (const level of [
      "Not assessed",
      "Low",
      "Moderate",
      "High",
      "Critical",
    ]) {
      expect(within(dialog).getByText(level)).toBeVisible();
    }
    expect(dialog).toHaveTextContent("incomplete safety information");
    expect(dialog).toHaveTextContent("the AI cannot downgrade");
    expect(dialog).toHaveTextContent("Resolved cases are excluded");
    expect(dialog).toHaveTextContent("not a validated mechanical diagnosis");
    await user.click(
      within(dialog).getByRole("button", { name: "Close urgency explanation" }),
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByText("Not assessed")).toBeVisible();
    expect(document.querySelectorAll(".overview-metric")).toHaveLength(3);
    expect(onStart).not.toHaveBeenCalled();
  });

  it("uses the API year and engine code and keeps gearbox and PR codes unconfirmed", async () => {
    const user = userEvent.setup();
    render(<App apiOverride={createDemoApi()} demoOverride={true} />);
    await screen.findByText("No active issues reported");
    expect(document.querySelector(".sidebar-vehicle small")).toHaveTextContent(
      "2009 · 2.0 TDI",
    );
    expect(document.querySelector(".topbar-vehicle")).toHaveTextContent("2009");
    await user.click(screen.getByRole("link", { name: "My Vehicle" }));
    expect(await screen.findByLabelText(/Engine code/)).toHaveValue("CFFB");
    expect(screen.getByText("Gearbox code")).toBeVisible();
    expect(screen.getByText("PR codes")).toBeVisible();
    expect(screen.getAllByText("Not confirmed")).toHaveLength(2);
  });
  it("shows an honest empty overview and transfers a draft without sending it", async () => {
    const api = createDemoApi();
    const diagnose = vi.spyOn(api, "diagnose");
    const user = userEvent.setup();
    render(<App apiOverride={api} demoOverride={true} />);
    await screen.findByText("Demo mode");
    const status = screen.getByRole("region", {
      name: "Latest consultation status",
    });
    expect(status.querySelectorAll(".overview-metric")).toHaveLength(3);
    expect(within(status).queryByText("Next step")).not.toBeInTheDocument();
    expect(within(status).getByText("Overall status")).toBeVisible();
    expect(within(status).getByText("Estimated urgency")).toBeVisible();
    expect(within(status).getByText("Available evidence")).toBeVisible();
    expect(await screen.findByText("No active issues reported")).toBeVisible();
    expect(screen.getByText("Not assessed")).toBeVisible();
    expect(screen.getByText("No diagnoses yet")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Loss of power" }));
    expect(screen.getByLabelText("Describe the symptoms")).toHaveValue(
      "I have noticed a loss of power in my car. ",
    );
    await waitFor(() =>
      expect(screen.getByLabelText("Describe the symptoms")).toBeEnabled(),
    );
    expect(diagnose).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Send consultation" }));
    await screen.findByRole("button", { name: "Open full report" });
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Open full report" }),
      ).toBeEnabled(),
    );
    await user.click(screen.getByRole("button", { name: "Open full report" }));
    expect(
      await screen.findByRole("heading", {
        name: "Recommended checks",
      }),
    ).toBeVisible();
    expect(
      screen.getByRole("heading", { name: "Available evidence" }),
    ).toBeVisible();
    expect(
      screen.getByRole("heading", { name: "Reported symptoms" }),
    ).toBeVisible();
    await user.click(screen.getByRole("link", { name: "Home" }));
    expect(
      await screen.findByRole("button", { name: "Resume diagnosis 1" }),
    ).toBeVisible();
    await user.click(
      screen.getByRole("button", { name: "Create a new diagnosis" }),
    );
    await waitFor(() =>
      expect(screen.getByLabelText("Describe the symptoms")).toHaveValue(""),
    );
    await user.click(screen.getByRole("link", { name: "Home" }));
    expect(
      await screen.findByRole("button", { name: "Resume diagnosis 1" }),
    ).toBeVisible();
  });

  it("retains critical driving advice on the overview", () => {
    render(
      <HomePage
        vehicle={demoVehicle}
        report={sampleReport(crypto.randomUUID(), true)}
        currentUrgency={{
          vehicle_id: demoVehicle.vehicle_id,
          urgency_level: "critical",
          active_case_count: 1,
          resolved_case_count: 0,
          explanation: "Active critical case",
        }}
        busy={false}
        onStart={vi.fn()}
        onSources={vi.fn()}
        onOpen={vi.fn()}
        onParts={vi.fn()}
        onVehicle={vi.fn()}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Do not continue driving",
    );
    expect(screen.getByText("Critical")).toBeVisible();
  });

  it("makes settings and help useful without inventing service availability", async () => {
    const user = userEvent.setup();
    window.location.hash = "configuracion";
    render(<App apiOverride={createDemoApi()} demoOverride={true} />);
    await screen.findByText("Demo mode");
    expect(screen.getByText("Not used in demo mode")).toBeVisible();
    await user.click(screen.getByRole("link", { name: "Help" }));
    expect(
      await screen.findByRole("heading", { name: "Check provenance" }),
    ).toBeVisible();
  });
});
