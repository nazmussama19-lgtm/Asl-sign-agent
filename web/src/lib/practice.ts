// Port of practice.py: word challenges and adaptive letter drills, scored letter by letter.
// Stats and labeled samples stay in the visitor's browser; samples can be downloaded as CSV.
import { load, remove, save } from "./storage";

export const LETTERS = "ABCDEFGHIKLMNOPQRSTUVWXY";   // J and Z are movements, out of the drill
export type Level = "Easy" | "Medium" | "Hard";

const WORDS: Record<"en" | "fr", Record<Level, string[]>> = {
  en: {
    Easy: ["CAT", "DOG", "SUN", "YES", "HI", "LOVE", "GOOD", "FUN", "TOP", "WIN"],
    Medium: ["HELLO", "WORLD", "HAPPY", "MUSIC", "SMILE", "DREAM", "LIGHT", "PEACE", "DANCE", "STORY"],
    Hard: ["FRIENDS", "MORNING", "AWESOME", "VICTORY", "HARMONY", "STRENGTH", "CREATIVE", "SUNSHINE"],
  },
  fr: {
    Easy: ["CHAT", "AMI", "OUI", "VIE", "ROI", "MER", "FEU", "LUNE", "PAIN", "MAIN"],
    Medium: ["SOLEIL", "BONNE", "MERCI", "AMOUR", "REVER", "DANSE", "MONDE", "COEUR", "SALUT", "MUSIQUE"],
    Hard: ["VICTOIRE", "COURAGE", "LUMIERE", "SOURIRE", "HARMONIE", "CREATIF", "MONTAGNE", "AVENTURE"],
  },
};

export interface Stats {
  letters: Record<string, { a: number; c: number }>;
  confusion: Record<string, number>;
  totals: { words: number; best_streak: number; samples: number };
}

const STATS_KEY = "asl.practiceStats";
const SAMPLES_KEY = "asl.practiceSamples";
const emptyStats = (): Stats => ({ letters: {}, confusion: {}, totals: { words: 0, best_streak: 0, samples: 0 } });

export const loadStats = () => load<Stats>(STATS_KEY, emptyStats());
export function resetStats() { remove(STATS_KEY); remove(SAMPLES_KEY); }

export function pickWord(mode: "letters" | "words", lang: "en" | "fr", level: Level, stats: Stats, rand = Math.random): string {
  if (mode === "letters") {
    const weights = [...LETTERS].map((L) => {
      const s = stats.letters[L] ?? { a: 0, c: 0 };
      return 0.15 + (s.a > 0 ? 1 - s.c / s.a : 0.5);       // unknown letters count as half-learned
    });
    let r = rand() * weights.reduce((a, b) => a + b, 0);
    for (let i = 0; i < LETTERS.length; i++) { r -= weights[i]; if (r <= 0) return LETTERS[i]; }
    return LETTERS[LETTERS.length - 1];
  }
  const pool = WORDS[lang][level].filter((w) => [...w].every((c) => LETTERS.includes(c)));
  return pool[Math.floor(rand() * pool.length)];
}

export interface Snapshot {
  word: string; idx: number; completed: boolean; active: boolean; score: number; streak: number;
  words: number; elapsed: number; lpm: number; lastEvent: { kind: "ok" | "err"; letter: string; t: number } | null;
}

export class PracticeEngine {
  stats: Stats = loadStats();
  private window: string[] = [];
  private word = "";
  private idx = 0;
  private active = false;
  private completed = false;
  private score = 0;
  private streak = 0;
  private sessionWords = 0;
  private startT: number | null = null;
  private endT: number | null = null;
  private lastDecision = -Infinity;
  private lastEvent: Snapshot["lastEvent"] = null;
  private samples: string[][] = [];

  constructor(private now: () => number = () => performance.now() / 1000) {}

  newSession() { this.score = 0; this.streak = 0; this.sessionWords = 0; this.lastEvent = null; }

  newWord(word: string) {
    this.word = word; this.idx = 0; this.completed = false; this.active = true;
    this.startT = this.now(); this.endT = null; this.window = [];
  }

  /** Called for every video frame with the model's prediction and the normalized landmarks. */
  update(label: string, conf: number, feats: Float32Array | null) {
    if (!this.active || this.completed || !this.word) return;
    const now = this.now();
    const top = conf >= 0.75 && LETTERS.includes(label) ? label : "nothing";
    this.window.push(top);
    if (this.window.length > 5) this.window.shift();
    const stable = top !== "nothing" && this.window.filter((v) => v === top).length >= 4 ? top : null;
    if (stable === null || now - this.lastDecision < 0.8) return;

    const target = this.word[this.idx];
    const st = (this.stats.letters[target] ??= { a: 0, c: 0 });
    st.a += 1;
    const correct = stable === target;
    if (feats) this.samples.push([...Array.from(feats, (v) => v.toFixed(5)), target, stable, correct ? "1" : "0", String(Math.round(Date.now() / 1000))]);
    if (correct) {
      st.c += 1;
      this.streak += 1;
      this.stats.totals.best_streak = Math.max(this.stats.totals.best_streak, this.streak);
      this.score += 10 + 2 * Math.min(this.streak, 10);     // capped streak multiplier
      this.idx += 1;
      this.lastEvent = { kind: "ok", letter: target, t: now };
      if (this.idx >= this.word.length) {
        this.completed = true;
        this.endT = now;
        this.score += 50;
        this.sessionWords += 1;
        this.stats.totals.words += 1;
        this.flush();
      }
    } else {
      const key = `${target}>${stable}`;
      this.stats.confusion[key] = (this.stats.confusion[key] ?? 0) + 1;
      this.streak = 0;
      this.lastEvent = { kind: "err", letter: stable, t: now };
    }
    this.lastDecision = now;
    this.window = [];
  }

  private flush() {
    if (this.samples.length) {
      const all = load<string[][]>(SAMPLES_KEY, []);
      all.push(...this.samples);
      save(SAMPLES_KEY, all.slice(-5000));
      this.stats.totals.samples += this.samples.length;
      this.samples = [];
    }
    save(STATS_KEY, this.stats);
  }

  snapshot(): Snapshot {
    const elapsed = this.startT !== null ? (this.endT ?? this.now()) - this.startT : 0;
    return {
      word: this.word, idx: this.idx, completed: this.completed, active: this.active, score: this.score,
      streak: this.streak, words: this.sessionWords, elapsed, lpm: elapsed > 1 ? (this.idx / elapsed) * 60 : 0,
      lastEvent: this.lastEvent,
    };
  }
}

/** Same columns as the Python app's assets/user_samples.csv. */
export function samplesCsv(): string {
  const header = [...Array.from({ length: 63 }, (_, i) => `f${i}`), "target", "predicted", "correct", "ts"].join(",");
  return [header, ...load<string[][]>(SAMPLES_KEY, []).map((r) => r.join(","))].join("\n") + "\n";
}
