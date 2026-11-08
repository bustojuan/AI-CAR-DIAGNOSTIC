import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { Vehicle3DViewer } from "../Vehicle3DViewer";

it("provides an English, honest missing-asset flow with draft-only AI/parts actions and keyboard return", async () => {
  const ask = vi.fn(),
    parts = vi.fn();
  const user = userEvent.setup();
  render(
    <Vehicle3DViewer
      model={null}
      explorer={{
        vehicle: {
          manufacturer: "Volkswagen",
          model: "Golf Plus",
          model_year: 2009,
          engine: "2.0 TDI",
        },
        engineBay: null,
        photo: null,
        onAskAI: ask,
        onFindParts: parts,
      }}
    />,
  );
  const launch = screen.getByRole("button", { name: "Explore Engine Bay" });
  await user.click(launch);
  expect(screen.getByRole("dialog", { name: "Engine Bay" })).toHaveAttribute(
    "lang",
    "en",
  );
  expect(
    screen.getByRole("heading", { name: "Engine bay asset unavailable" }),
  ).toBeVisible();
  expect(document.querySelector("canvas")).toBeNull();
  expect(ask).not.toHaveBeenCalled();
  expect(parts).not.toHaveBeenCalled();
  await user.click(
    screen.getByRole("button", { name: "Battery General topic" }),
  );
  expect(screen.getByRole("heading", { name: "Battery" })).toBeVisible();
  expect(
    screen.getByText(/No vehicle-specific technical evidence/),
  ).toBeVisible();
  await user.click(
    screen.getByRole("button", { name: "Ask AI About This Component" }),
  );
  expect(ask.mock.calls[0][0]).toContain(
    "No component fault has been confirmed",
  );
  await user.click(screen.getByRole("button", { name: "Find Related Parts" }));
  expect(parts).toHaveBeenCalledWith("battery");
  await user.keyboard("{Escape}");
  await waitFor(() =>
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
  );
  expect(launch).toHaveFocus();
  expect(document.body.style.overflow).not.toBe("hidden");
});
