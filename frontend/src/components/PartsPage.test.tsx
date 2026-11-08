import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { createDemoApi, demoVehicle, sampleTool } from "../demo/api";
import { PartsPage } from "./PartsPage";

function offer() {
  const result = sampleTool("search_parts");
  return {
    ...result,
    provider: "ebay" as const,
    demo_data: false,
    verification: "verified_provider" as const,
    parts: [
      {
        ...result.parts![0],
        part_id: "EBAY-123-0",
        name: "Transient offer",
        source: "ebay",
        source_url: "https://www.ebay.es/itm/123",
        verification: "verified_provider" as const,
      },
    ],
  };
}

it("keeps offers out of browser storage and clears them when leaving the page", async () => {
  const api = createDemoApi();
  vi.spyOn(api, "search").mockResolvedValue(offer());
  const local = vi.spyOn(Storage.prototype, "setItem");
  const user = userEvent.setup();
  render(
    <PartsPage api={api} vehicle={demoVehicle} initialComponent="glow plugs" />,
  );
  await user.click(screen.getByRole("button", { name: "Search candidates" }));
  expect(await screen.findByText("Transient offer")).toBeInTheDocument();
  expect(screen.getByText(/Temporary offers only/)).toBeInTheDocument();
  expect(local).not.toHaveBeenCalled();
  fireEvent(window, new Event("pagehide"));
  expect(screen.queryByText("Transient offer")).not.toBeInTheDocument();
});

it("does not restore an in-flight offer after the page has been hidden", async () => {
  const api = createDemoApi();
  let complete!: (result: ReturnType<typeof offer>) => void;
  vi.spyOn(api, "search").mockReturnValue(
    new Promise((resolve) => {
      complete = resolve;
    }),
  );
  const user = userEvent.setup();
  render(
    <PartsPage api={api} vehicle={demoVehicle} initialComponent="glow plugs" />,
  );
  await user.click(screen.getByRole("button", { name: "Search candidates" }));
  fireEvent(window, new Event("pagehide"));
  await act(async () => complete(offer()));
  expect(screen.queryByText("Transient offer")).not.toBeInTheDocument();
});
