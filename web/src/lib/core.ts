// Port of asl_core.py and word_signs.py (features): same maths, so the models see the same inputs.

export type Landmarks = number[][];   // 21 x [x, y, z]

/** Recentre on the wrist and scale by wrist -> middle-finger base (x, y). Returns 63 values. */
export function normalizeLandmarks(lm: Landmarks): Float32Array {
  const [wx, wy, wz] = lm[0];
  let scale = Math.hypot(lm[9][0] - wx, lm[9][1] - wy);
  if (scale < 1e-6) scale = 1e-6;
  const out = new Float32Array(63);
  lm.forEach(([x, y, z], i) => {
    out[i * 3] = (x - wx) / scale;
    out[i * 3 + 1] = (y - wy) / scale;
    out[i * 3 + 2] = (z - wz) / scale;
  });
  return out;
}

export const SEQ_LEN = 32;
export const FRAME_DIM = 126;   // left hand (63) + right hand (63), zeros when absent

export function buildFrameFeatures(left: Landmarks | null, right: Landmarks | null): Float32Array {
  const out = new Float32Array(FRAME_DIM);
  if (left) out.set(normalizeLandmarks(left), 0);
  if (right) out.set(normalizeLandmarks(right), 63);
  return out;
}

/** (T, 126) -> (n, 126) by linear interpolation along time. */
export function resampleSequence(frames: Float32Array[], n = SEQ_LEN): Float32Array {
  const out = new Float32Array(n * FRAME_DIM);
  if (frames.length === 0) return out;
  if (frames.length === 1) {
    for (let i = 0; i < n; i++) out.set(frames[0], i * FRAME_DIM);
    return out;
  }
  for (let i = 0; i < n; i++) {
    const src = (i * (frames.length - 1)) / (n - 1);
    const lo = Math.floor(src), hi = Math.ceil(src), w = src - lo;
    for (let c = 0; c < FRAME_DIM; c++) out[i * FRAME_DIM + c] = frames[lo][c] * (1 - w) + frames[hi][c] * w;
  }
  return out;
}

/** Turns a noisy stream of per-frame predictions into committed letters. */
export class SentenceBuilder {
  confThreshold = 0.8;
  stabThreshold = 4;
  cooldown = 0.6;
  private window: string[] = [];
  private sentence = "";
  private committed: string | null = null;
  private lastCommit = 0;

  constructor(private stabWindow = 5, private now: () => number = () => performance.now() / 1000) {}

  update(label: string, conf: number): string {
    const top = conf >= this.confThreshold ? label : "nothing";
    this.window.push(top);
    if (this.window.length > this.stabWindow) this.window.shift();
    const count = this.window.filter((v) => v === top).length;
    const stable = count >= this.stabThreshold ? top : null;
    if (stable !== null && stable !== this.committed) {
      if (stable === "nothing") this.committed = null;
      else if (this.now() - this.lastCommit >= this.cooldown) {
        this.apply(stable);
        this.committed = stable;
        this.lastCommit = this.now();
      }
    }
    return this.sentence;
  }

  commit(letter: string): string {
    if (this.now() - this.lastCommit >= this.cooldown) {
      this.apply(letter);
      this.committed = letter;
      this.lastCommit = this.now();
    }
    return this.sentence;
  }

  private apply(token: string) {
    if (token === "space") this.sentence += " ";
    else if (token === "del") this.sentence = this.sentence.slice(0, -1);
    else if (token !== "nothing") this.sentence += token;
  }

  /** A recognized word sign, followed by a space. */
  commitWord(word: string) {
    if (this.sentence && !this.sentence.endsWith(" ")) this.sentence += " ";
    this.sentence += word.toUpperCase() + " ";
    this.committed = null;
    this.lastCommit = this.now();
  }

  /** Replace the word being spelled by an accepted suggestion (thumbs up). */
  acceptWord(word: string) {
    const parts = this.sentence.split(" ");
    parts[parts.length - 1] = word;
    this.sentence = parts.join(" ") + " ";
    this.committed = null;
    this.lastCommit = this.now();
  }

  addSpace() { this.sentence += " "; }
  delete() { this.sentence = this.sentence.slice(0, -1); }
  clear() { this.sentence = ""; this.committed = null; }
  get() { return this.sentence; }
  /** Test hook: forget the last committed letter so the same one can be committed again. */
  resetCommitted() { this.committed = null; }
}

/** J and Z from motion, gated by the starting pose. Static letters are blocked while moving. */
export class DynamicDetector {
  moveThreshold = 0.12;
  private speeds: number[] = [];
  private active = false;
  private prev: [number[], number[]] | null = null;
  private startPose: string | null = null;
  private pathIndex = 0;
  private pathPinky = 0;
  private dirChanges = 0;
  private lastDx = 0;

  constructor(private windowSize = 8, private minPath = 0.2) {}

  update(lm: Landmarks, currentStaticLabel: string | null): { moving: boolean; letter: string | null } {
    const idx = [lm[8][0], lm[8][1]];
    const pky = [lm[20][0], lm[20][1]];
    let moving = false;
    let letter: string | null = null;
    if (this.prev) {
      const dIdx = Math.hypot(idx[0] - this.prev[0][0], idx[1] - this.prev[0][1]);
      const dPky = Math.hypot(pky[0] - this.prev[1][0], pky[1] - this.prev[1][1]);
      this.speeds.push(Math.max(dIdx, dPky));
      if (this.speeds.length > this.windowSize) this.speeds.shift();
      if (this.speeds.reduce((a, b) => a + b, 0) > this.moveThreshold) {
        moving = true;
        if (!this.active) {
          this.active = true;
          this.startPose = currentStaticLabel;
          this.pathIndex = this.pathPinky = 0;
          this.dirChanges = 0;
          this.lastDx = 0;
        }
        this.pathIndex += dIdx;
        this.pathPinky += dPky;
        const dx = idx[0] - this.prev[0][0];
        const s = dx > 0.004 ? 1 : dx < -0.004 ? -1 : 0;
        if (s !== 0) {
          if (this.lastDx !== 0 && s !== this.lastDx) this.dirChanges += 1;
          this.lastDx = s;
        }
      } else if (this.active) {
        this.active = false;
        if (this.pathIndex + this.pathPinky > this.minPath) {
          if (this.startPose === "I" && this.pathPinky >= 0.6 * this.pathIndex) letter = "J";
          else if (this.dirChanges >= 2 && this.pathIndex > this.pathPinky) letter = "Z";
        }
      }
    }
    this.prev = [idx, pky];
    return { moving, letter };
  }
}

/** Thumb clearly above, the four other fingers folded. Image coordinates (y grows downward). */
export function isThumbsUp(lm: Landmarks): boolean {
  const thumbUp = lm[4][1] < lm[3][1] - 0.02 && lm[4][1] < lm[5][1] - 0.05;
  const folded = ([[8, 6], [12, 10], [16, 14], [20, 18]] as const).every(([t, p]) => lm[t][1] > lm[p][1]);
  return thumbUp && folded;
}

/** Collects frames while a gesture is moving; returns the sequence when it stops. */
export class GestureEpisode {
  private frames: Float32Array[] = [];
  private active = false;
  constructor(private minFrames = 12) {}

  step(moving: boolean, feat: Float32Array): Float32Array[] | null {
    if (moving) {
      this.active = true;
      this.frames.push(feat);
      return null;
    }
    if (this.active) {
      this.active = false;
      const seq = this.frames;
      this.frames = [];
      if (seq.length >= this.minFrames) return seq;
    }
    return null;
  }
}
