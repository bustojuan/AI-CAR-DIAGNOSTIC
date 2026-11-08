import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { App } from "../App";
import { createDemoApi, demoVehicle } from "../demo/api";
import { ApiError } from "../api/client";

vi.mock("./vehicle3d/asset", () => ({
  dashboardVehicleModel: null,
  golfPlusEngineBay: null,
}));

it("confirms resolution, saves a note, filters history and refreshes dashboard urgency on reopen", async () => {
  const api = createDemoApi();
  const report = await api.diagnose(demoVehicle.vehicle_id, {
    description: "My brakes failed.",
  });
  const resolve = vi.spyOn(api, "resolveCase");
  const refresh = vi.spyOn(api, "caseHistory");
  const user = userEvent.setup();
  window.location.hash = "historial";
  render(<App apiOverride={api} demoOverride={false} />);
  await screen.findByRole("button", { name: "Mark as Resolved" });
  await user.click(screen.getByRole("button", { name: "Mark as Resolved" }));
  let dialog = screen.getByRole("dialog", {
    name: "Mark this case as resolved?",
  });
  expect(within(dialog).getByText(/does not independently/)).toBeVisible();
  expect(resolve).not.toHaveBeenCalled();
  await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
  expect(resolve).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Mark as Resolved" }));
  dialog = screen.getByRole("dialog");
  await user.type(
    within(dialog).getByLabelText("Resolution note (optional)"),
    "Workshop visit completed.",
  );
  await user.click(
    within(dialog).getByRole("button", { name: "Confirm Resolution" }),
  );
  await screen.findByRole("button", { name: "Reopen Diagnosis" });
  expect(
    screen.getByText("Resolution note: Workshop visit completed."),
  ).toBeVisible();
  expect(screen.getByText(/Resolved on/)).toBeVisible();
  expect(resolve).toHaveBeenCalledWith(report.conversation_id, {
    expected_latest_diagnostic_id: report.diagnostic_id,
    resolution_note: "Workshop visit completed.",
  });
  await user.click(screen.getByRole("button", { name: "Active" }));
  expect(
    screen.getByRole("heading", { name: "No active cases" }),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Resolved" }));
  expect(
    screen.getByRole("button", { name: "Reopen Diagnosis" }),
  ).toBeVisible();
  await user.click(screen.getByRole("link", { name: "Home" }));
  const status = screen.getByRole("region", {
    name: "Latest consultation status",
  });
  expect(within(status).getByText("Not assessed")).toBeVisible();
  expect(within(status).getByText("No active issues reported")).toBeVisible();
  await user.click(screen.getByRole("link", { name: "History" }));
  await user.click(screen.getByRole("button", { name: "Reopen Diagnosis" }));
  await screen.findByRole("button", { name: "Mark as Resolved" });
  await user.click(screen.getByRole("link", { name: "Home" }));
  expect(await screen.findByText("Critical", { exact: true })).toBeVisible();
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Do not continue driving",
  );
  expect(refresh.mock.calls.length).toBeGreaterThanOrEqual(3);
  expect(await api.diagnostic(report.diagnostic_id)).toEqual(report);
});

it("retrieves server history without browser-local links and survives a page remount", async () => {
  const api = createDemoApi();
  const report = await api.diagnose(demoVehicle.vehicle_id, {
    description: "Cold starting problem.",
  });
  await api.resolveCase(report.conversation_id, {
    expected_latest_diagnostic_id: report.diagnostic_id,
  });
  window.location.hash = "historial";
  const first = render(<App apiOverride={api} demoOverride={false} />);
  await screen.findByRole("button", { name: "Reopen Diagnosis" });
  expect(localStorage.length).toBe(0);
  first.unmount();
  render(<App apiOverride={api} demoOverride={false} />);
  expect(
    await screen.findByRole("button", { name: "Reopen Diagnosis" }),
  ).toBeVisible();
  expect(screen.getByText("Resolved", { selector: ".badge" })).toBeVisible();
});

it("keeps uncertainty visible when status was saved but refresh failed", async () => {
  const api = createDemoApi();
  const report = await api.diagnose(demoVehicle.vehicle_id, {
    description: "My brakes failed.",
  });
  const refresh = vi.spyOn(api, "caseHistory");
  const user = userEvent.setup();
  window.location.hash = "historial";
  render(<App apiOverride={api} demoOverride={false} />);
  await screen.findByRole("button", { name: "Mark as Resolved" });
  await user.click(screen.getByRole("button", { name: "Mark as Resolved" }));
  refresh.mockRejectedValueOnce(new ApiError("Disconnected"));
  await user.click(screen.getByRole("button", { name: "Confirm Resolution" }));
  await screen.findByText(/Case status was saved/);
  expect(
    (await api.conversation(report.conversation_id)).resolution_status,
  ).toBe("resolved");
  await user.click(screen.getByRole("button", { name: "Refresh history" }));
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Reopen Diagnosis" }),
    ).toBeVisible(),
  );
});
