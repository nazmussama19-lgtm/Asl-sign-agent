// Same checks as tests/test_core.py, on the TypeScript ports.
import { describe, expect, it } from "vitest";
import { DynamicDetector, SentenceBuilder, buildFrameFeatures, countStrokes, handShape, isThumbsUp, normalizeLandmarks, resampleSequence, type Landmarks } from "./core";
import { CustomSigns, PersonalLetters } from "./personal";
import { LETTERS, PracticeEngine, loadStats, pickWord } from "./practice";

const rand = (n: number) => Array.from({ length: n }, () => [Math.random(), Math.random(), Math.random()]);

describe("core", () => {
  it("normalization is invariant to translation and scale", () => {
    const lm = rand(21);
    const base = normalizeLandmarks(lm);
    const shifted = normalizeLandmarks(lm.map(([x, y, z]) => [x + 0.3, y - 0.2, z + 0.1]));
    const scaled = normalizeLandmarks(lm.map((p) => p.map((v) => v * 2.5)));
    base.forEach((v, i) => { expect(shifted[i]).toBeCloseTo(v, 4); expect(scaled[i]).toBeCloseTo(v, 3); });
    expect(base.length).toBe(63);
  });

  it("sentence builder handles space and delete", () => {
    let t = 0;
    const b = new SentenceBuilder(1, () => (t += 1));
    b.stabThreshold = 1; b.cooldown = 0;
    for (const tok of ["H", "I", "space", "A", "del"]) { b.update(tok, 0.99); b.resetCommitted(); }
    expect(b.get()).toBe("HI ");
  });

  it("thumbs up geometry", () => {
    const lm: Landmarks = Array.from({ length: 21 }, () => [0, 0, 0]);
    lm[0] = [0.5, 0.9, 0]; lm[3] = [0.45, 0.65, 0]; lm[4] = [0.45, 0.5, 0]; lm[5] = [0.5, 0.7, 0];
    for (const [t, p] of [[8, 6], [12, 10], [16, 14], [20, 18]]) { lm[p] = [0.55, 0.75, 0]; lm[t] = [0.55, 0.85, 0]; }
    expect(isThumbsUp(lm)).toBe(true);
    for (const t of [8, 12, 16, 20]) lm[t] = [0.55, 0.55, 0];
    expect(isThumbsUp(lm)).toBe(false);
  });

  it("word-sign features and custom sign matching", () => {
    const f = buildFrameFeatures(rand(21), null);
    expect(f.length).toBe(126);
    expect([...f.slice(63)].every((v) => v === 0)).toBe(true);
    expect(resampleSequence(Array(7).fill(f)).length).toBe(32 * 126);
    const base = Array.from({ length: 20 }, () => Float32Array.from({ length: 126 }, () => Math.random()));
    const noisy = () => base.map((fr) => fr.map((v) => v + (Math.random() - 0.5) * 0.02));
    const store = new CustomSigns("test.custom");
    store.add("A", noisy()); store.add("A", noisy());
    const other = () => Array.from({ length: 20 }, () => Float32Array.from({ length: 126 }, () => Math.random()));
    store.add("B", other()); store.add("B", other());
    const m = store.match(base);
    expect(m.name).toBe("A");
    expect(m.score).toBeGreaterThan(0.9);
  });

  it("personal letters override the model when very close", () => {
    const pl = new PersonalLetters(0.32, "test.personal");
    pl.reset();
    const feats = Float32Array.from({ length: 63 }, () => Math.random());
    pl.add("M", feats);
    const r = pl.refine(feats.map((v) => v + 0.01), "N", 0.5);
    expect(r).toEqual({ label: "M", conf: 0.95, used: true });
    expect(pl.refine(feats.map((v) => v * 5 + 3), "N", 0.5).used).toBe(false);
  });

  it("practice engine flow", () => {
    let t = 0;
    const eng = new PracticeEngine(() => t);
    eng.newSession(); eng.newWord("HI");
    const feats = new Float32Array(63);
    for (const label of ["H", "K", "I"]) {
      for (let i = 0; i < 5; i++) eng.update(label, 0.95, feats);
      t += 0.85;
    }
    const s = eng.snapshot();
    expect(s.completed).toBe(true);
    expect(s.idx).toBe(2);
    expect(eng.stats.confusion["I>K"]).toBe(1);
    expect(LETTERS.includes("J") || LETTERS.includes("Z")).toBe(false);
    expect(LETTERS).toContain(pickWord("letters", "fr", "Easy", loadStats()));
  });

  // ---------- J / Z (same cases as tests/test_core.py) ----------
  const INDEX = [true, false, false, false], PINKY = [false, false, false, true], OPEN = [true, true, true, true];
  function hand(extended: boolean[], dx = 0, dy = 0): Landmarks {
    const lm: Landmarks = Array.from({ length: 21 }, () => [0, 0, 0]);
    lm[0] = [0.5, 0.8, 0];
    [[0.44, 0.74], [0.40, 0.70], [0.38, 0.66], [0.37, 0.63]].forEach(([x, y], i) => { lm[1 + i] = [x, y, 0]; });
    [5, 9, 13, 17].forEach((base, f) => {
      const x = 0.44 + 0.04 * f;
      lm[base] = [x, 0.62, 0];
      lm[base + 1] = [x, 0.55, 0];
      if (extended[f]) { lm[base + 2] = [x, 0.49, 0]; lm[base + 3] = [x, 0.43, 0]; }
      else { lm[base + 2] = [x, 0.60, 0]; lm[base + 3] = [x, 0.64, 0]; }
    });
    return lm.map(([x, y, z]) => [x + dx, y + dy, z]);
  }
  function run(frames: Landmarks[], label: string | null = null) {
    const det = new DynamicDetector();
    let out: string | null = null;
    for (const lm of [...frames, ...Array(12).fill(frames[frames.length - 1])]) out = det.update(lm, label).letter ?? out;
    return out;
  }
  const zPath = (shape: boolean[]) => [
    ...Array.from({ length: 8 }, (_, i) => hand(shape, i * 0.02, 0)),
    ...Array.from({ length: 8 }, (_, i) => hand(shape, 0.14 - i * 0.02, i * 0.012)),
    ...Array.from({ length: 8 }, (_, i) => hand(shape, i * 0.02, 0.096)),
  ];

  it("hand shapes and strokes", () => {
    expect(handShape(hand(INDEX))).toBe("index");
    expect(handShape(hand(PINKY))).toBe("pinky");
    expect(handShape(hand(OPEN))).toBe(null);
    expect(countStrokes([0, 0.1, 0.0, 0.1], 0.04)).toBe(3);
    expect(countStrokes([0, 0.01, 0.0, 0.012, 0.001], 0.04)).toBe(0);
  });

  it("Z needs the Z shape", () => {
    expect(run(zPath(INDEX))).toBe("Z");
    expect(run(zPath(OPEN))).toBe(null);
    expect(run(Array.from({ length: 12 }, (_, i) => hand(INDEX, i * 0.02, 0)))).toBe(null);
  });

  it("J needs the I pose and the little finger", () => {
    const hook = Array.from({ length: 12 }, (_, i) => hand(PINKY, i > 6 ? -i * 0.01 : 0, i * 0.02));
    expect(run(hook, "I")).toBe("J");
    expect(run(hook, "A")).toBe(null);
  });
});
