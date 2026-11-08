import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { Vehicle3DViewer } from "./Vehicle3DViewer";

it("preserves the selected Golf render and never advertises 360 interaction without an authorized model", () => {
  render(<Vehicle3DViewer model={null} />);
  expect(screen.getByRole("img")).toHaveAttribute(
    "src",
    "/images/golf-viii-gti-poster.png",
  );
  expect(screen.getByText("Static image · 3D model unavailable")).toBeVisible();
  expect(document.querySelector("canvas")).toBeNull();
  expect(screen.queryByText(/Drag to explore/)).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Reset vehicle view" }),
  ).not.toBeInTheDocument();
});
