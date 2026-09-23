import { describe, expect, it } from "vitest";
import { handWindow, isPrivacy, MODES, PRIVACY_HINT, PRIVACY_LABEL, SMOOTH, type Circle } from "./privacy";

const square = (cx: number, cy: number, half: number): [number, number][] => [
  [cx - half, cy - half],
  [cx + half, cy - half],
  [cx + half, cy + half],
  [cx - half, cy + half],
];

describe("privacy modes", () => {
  it("only accepts the three known modes", () => {
    for (const m of MODES) expect(isPrivacy(m)).toBe(true);
    for (const bad of ["blur", "", null, undefined, 3, {}]) expect(isPrivacy(bad)).toBe(false);
  });

  it("labels and hints every mode", () => {
    for (const m of MODES) {
      expect(PRIVACY_LABEL[m].length).toBeGreaterThan(0);
      expect(PRIVACY_HINT[m].length).toBeGreaterThan(0);
    }
  });
});

describe("handWindow", () => {
  it("centres on the hand", () => {
    const w = handWindow(square(200, 150, 40), 640, 480);
    expect(w.x).toBeCloseTo(200);
    expect(w.y).toBeCloseTo(150);
  });

  it("covers more than the hand itself", () => {
    const half = 40;
    const w = handWindow(square(320, 240, half), 640, 480);
    expect(w.r).toBeGreaterThan(half);
  });

  it("never grows wider than the stage", () => {
    const w = handWindow(square(320, 240, 400), 640, 480);
    expect(w.r).toBeLessThanOrEqual(Math.min(640, 480) * 0.48);
  });

  it("glides towards the new position instead of jumping", () => {
    const prev: Circle = { x: 100, y: 100, r: 80 };
    const next = handWindow(square(300, 100, 40), 640, 480, prev);
    expect(next.x).toBeGreaterThan(prev.x);
    expect(next.x).toBeLessThan(300);
    expect(next.x).toBeCloseTo(prev.x + (300 - prev.x) * SMOOTH);
  });

  it("settles on the target after enough frames", () => {
    let win = handWindow(square(300, 200, 40), 640, 480);
    for (let i = 0; i < 60; i++) win = handWindow(square(300, 200, 40), 640, 480, win);
    expect(win.x).toBeCloseTo(300, 3);
    expect(win.y).toBeCloseTo(200, 3);
  });
});
