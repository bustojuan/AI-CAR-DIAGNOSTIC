import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { EngineBayPhotoViewer } from "./EngineBayPhotoViewer";
import { engineBayPhoto } from "./photo";

it("shows an attributed full-compartment reference, reviewed markers and bounded zoom/reset", async () => {
  const onSelect = vi.fn();
  const user = userEvent.setup();
  render(
    <EngineBayPhotoViewer
      asset={engineBayPhoto}
      selected="engine"
      onSelect={onSelect}
    />,
  );
  const image = screen.getByRole("img");
  expect(image).toHaveAttribute("src", engineBayPhoto.src);
  expect(screen.getByText(engineBayPhoto.notice)).toBeVisible();
  expect(
    screen.getByRole("link", { name: engineBayPhoto.license }),
  ).toHaveAttribute("href", engineBayPhoto.licenseUrl);
  fireEvent.load(image);
  expect(screen.getAllByRole("button", { name: /in photograph/ })).toHaveLength(
    3,
  );
  expect(
    screen.queryByRole("button", { name: "Inspect Battery in photograph" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", {
      name: "Inspect Engine cover in photograph",
    }),
  ).not.toBeInTheDocument();
  await user.click(
    screen.getByRole("button", {
      name: "Inspect Coolant expansion tank in photograph",
    }),
  );
  expect(onSelect).toHaveBeenCalledWith("coolant");
  await user.click(screen.getByRole("button", { name: "Zoom in engine bay" }));
  expect(screen.getByLabelText("Engine bay zoom")).toHaveTextContent("125%");
  const viewport = screen.getByRole("region", {
    name: "Engine compartment photograph",
  });
  viewport.focus();
  for (let i = 0; i < 10; i++) await user.keyboard("+");
  expect(screen.getByLabelText("Engine bay zoom")).toHaveTextContent("350%");
  await user.click(
    screen.getByRole("button", { name: "Reset engine bay photograph" }),
  );
  expect(screen.getByLabelText("Engine bay zoom")).toHaveTextContent("100%");
});

it("handles a failed image without inventing positions or implying a working photo", () => {
  render(
    <EngineBayPhotoViewer
      asset={engineBayPhoto}
      selected={null}
      onSelect={vi.fn()}
    />,
  );
  fireEvent.error(screen.getByRole("img"));
  expect(screen.getByText(/The photograph could not be loaded/)).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Zoom in engine bay" }),
  ).toBeDisabled();
  expect(
    screen.queryByRole("button", { name: /in photograph/ }),
  ).not.toBeInTheDocument();
});
