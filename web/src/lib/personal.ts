// Personal data kept in the visitor's browser: letter examples (few-shot k-NN), custom signs
// (cosine similarity on resampled sequences). Ports of personal.py and word_signs.CustomSignStore.
import { resampleSequence } from "./core";
import { load, save } from "./storage";

export class PersonalLetters {
  private X: Float32Array[] = [];
  private y: string[] = [];

  constructor(private threshold = 0.32, private key = "asl.personalLetters") {
    const raw = load<{ y: string[]; X: number[][] }>(key, { y: [], X: [] });
    this.y = raw.y;
    this.X = raw.X.map((r) => Float32Array.from(r));
  }

  add(letter: string, feats: Float32Array): number {
    this.X.push(Float32Array.from(feats));
    this.y.push(letter);
    this.persist();
    return this.y.filter((l) => l === letter).length;
  }

  counts(): Record<string, number> {
    const out: Record<string, number> = {};
    for (const l of this.y) out[l] = (out[l] ?? 0) + 1;
    return out;
  }

  reset() { this.X = []; this.y = []; this.persist(); }

  /** A very close personal example wins over the model. */
  refine(feats: Float32Array, label: string, conf: number): { label: string; conf: number; used: boolean } {
    let best = Infinity, bi = -1;
    this.X.forEach((x, i) => {
      let d = 0;
      for (let k = 0; k < 63; k++) d += (x[k] - feats[k]) ** 2;
      if (d < best) { best = d; bi = i; }
    });
    if (bi >= 0 && Math.sqrt(best) <= this.threshold) return { label: this.y[bi], conf: Math.max(conf, 0.95), used: true };
    return { label, conf, used: false };
  }

  private persist() { save(this.key, { y: this.y, X: this.X.map((x) => Array.from(x, (v) => +v.toFixed(5))) }); }
}

export class CustomSigns {
  private templates: Record<string, Float32Array[]> = {};

  constructor(private key = "asl.customSigns") {
    const raw = load<Record<string, number[][]>>(key, {});
    for (const [k, list] of Object.entries(raw)) this.templates[k] = list.map((v) => Float32Array.from(v));
  }

  add(name: string, frames: Float32Array[]): number {
    (this.templates[name] ??= []).push(resampleSequence(frames));
    this.persist();
    return this.templates[name].length;
  }

  delete(name: string) { delete this.templates[name]; this.persist(); }

  names(): Record<string, number> {
    return Object.fromEntries(Object.entries(this.templates).map(([k, v]) => [k, v.length]));
  }

  match(frames: Float32Array[], threshold = 0.86): { name: string | null; score: number } {
    const q = resampleSequence(frames);
    const qn = Math.hypot(...q);
    if (qn < 1e-6) return { name: null, score: 0 };
    let best = -1, bestName: string | null = null;
    for (const [name, list] of Object.entries(this.templates)) {
      if (list.length < 2) continue;          // at least two examples
      for (const t of list) {
        const tn = Math.hypot(...t);
        if (tn < 1e-6) continue;
        let dot = 0;
        for (let i = 0; i < q.length; i++) dot += q[i] * t[i];
        const sim = dot / (qn * tn);
        if (sim > best) { best = sim; bestName = name; }
      }
    }
    return best >= threshold ? { name: bestName, score: best } : { name: null, score: best };
  }

  private persist() {
    save(this.key, Object.fromEntries(Object.entries(this.templates).map(([k, v]) => [k, v.map((t) => Array.from(t, (x) => +x.toFixed(4)))])));
  }
}
