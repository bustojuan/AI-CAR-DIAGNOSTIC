import { describe, expect, it } from "vitest";
import { Group, Mesh } from "three";
import { componentDraft, engineBayAvailability } from "./components";
import { resolveBinding } from "./picking";
import type { EngineBayAsset, VehicleIdentity } from "./types";

const vehicle: VehicleIdentity = {
  manufacturer: "Volkswagen",
  model: "Golf Plus",
  model_year: 2009,
  engine: "2.0 TDI",
  engine_code: "TEST",
};
const asset: EngineBayAsset = {
  model: {
    src: "/test.glb",
    name: "TEST ONLY",
    author: "Test",
    license: "Test",
  },
  vehicle: { ...vehicle, engine_code: "TEST" },
  verified: true,
  verifiedBy: "Test harness",
  components: [],
};

describe("engine-bay applicability gate", () => {
  it("rejects absent, unreviewed and incorrect-vehicle models", () => {
    expect(engineBayAvailability(null, vehicle)).toMatch(/not been supplied/);
    expect(
      engineBayAvailability({ ...asset, verified: false }, vehicle),
    ).toMatch(/not been verified/);
    expect(
      engineBayAvailability({ ...asset, verifiedBy: " " }, vehicle),
    ).toMatch(/not been verified/);
    expect(
      engineBayAvailability(
        { ...asset, vehicle: { ...asset.vehicle, model_year: 2011 } },
        vehicle,
      ),
    ).toMatch(/does not match the diagnostic vehicle/);
  });
  it("requires the actual engine code and accepts only a reviewed match", () => {
    expect(
      engineBayAvailability(asset, { ...vehicle, engine_code: null }),
    ).toMatch(/must be confirmed/);
    expect(
      engineBayAvailability(asset, { ...vehicle, engine_code: "OTHER" }),
    ).toMatch(/engine code/);
    expect(engineBayAvailability(asset, vehicle)).toBeNull();
  });
});

it("uses explicit mesh ancestry and never guesses by name fragments or spatial position", () => {
  const hood = new Group();
  hood.name = "Hood";
  const child = new Mesh();
  child.name = "Panel";
  hood.add(child);
  const bindings = [{ id: "hood", label: "Hood", meshNames: ["Hood"] }];
  expect(resolveBinding(child, bindings)?.id).toBe("hood");
  const unrelated = new Mesh();
  unrelated.name = "HoodLikePanel";
  expect(resolveBinding(unrelated, bindings)).toBeNull();
});

it("prepares a question without converting common symptoms into claimed observations", () => {
  const draft = componentDraft("battery", vehicle);
  expect(draft).toContain("Volkswagen Golf Plus 2009 2.0 TDI");
  expect(draft).toContain("No component fault has been confirmed");
  expect(draft).not.toContain("Slow cranking");
  expect(draft).toMatch(/My observed symptoms are: $/);
});
