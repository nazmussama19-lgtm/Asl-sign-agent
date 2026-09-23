// Port of agent.py: turns a raw fingerspelled stream into a clean sentence, and explains each step.
import { getCloseMatches } from "./difflib";

const ABBREV: Record<string, string> = {
  // English
  U: "you", R: "are", UR: "your", YR: "your", Y: "why", N: "and", B: "be", C: "see", K: "ok", OK: "ok",
  THX: "thanks", TY: "thank you", PLS: "please", PLZ: "please", BC: "because", BCS: "because",
  W: "with", WO: "without", TMR: "tomorrow", TMRW: "tomorrow", TDY: "today", RN: "right now",
  MSG: "message", NVM: "nevermind", IDK: "i dont know", BRB: "be right back", OMW: "on my way",
  ILY: "i love you",
  // French
  BJR: "bonjour", SLT: "salut", CC: "coucou", CV: "ca va", MRC: "merci", BCP: "beaucoup",
  DSL: "desole", STP: "s'il te plait", SVP: "s'il vous plait", PK: "pourquoi", PCQ: "parce que",
  AJD: "aujourd'hui", MTN: "maintenant", TT: "tout", TLM: "tout le monde", JSP: "je sais pas",
  JTM: "je t'aime", QQN: "quelqu'un", QQCH: "quelque chose", RDV: "rendez-vous", STV: "si tu veux",
};

export interface Interpretation { text: string; journal: string[] }

export class Vocabulary {
  readonly words: string[] = [];
  readonly rank = new Map<string, number>();
  readonly byLen = new Map<number, string[]>();
  readonly fr: Set<string>;
  readonly en: Set<string>;
  readonly all: Set<string>;

  constructor(frWords: string[], enWords: string[]) {
    for (const list of [frWords, enWords]) {
      list.forEach((w, i) => {
        if (w.length === 1 && w !== "A" && w !== "I") return;
        if (!this.rank.has(w)) { this.rank.set(w, i); this.words.push(w); }
      });
    }
    for (const w of this.words) {
      const list = this.byLen.get(w.length);
      if (list) list.push(w); else this.byLen.set(w.length, [w]);
    }
    this.fr = new Set(frWords);
    this.en = new Set(enWords);
    this.all = new Set(this.words);
  }

  static fromText(fr: string, en: string) {
    const split = (s: string) => s.split(/\s+/).filter(Boolean);
    return new Vocabulary(split(fr), split(en));
  }
}

export class Agent {
  private closeCache = new Map<string, string | null>();
  private costCache = new Map<string, number>();

  constructor(private vocab: Vocabulary) {}

  private close(word: string): string | null {
    const hit = this.closeCache.get(word);
    if (hit !== undefined) return hit;
    const cands: string[] = [];
    for (const L of [word.length - 1, word.length, word.length + 1]) cands.push(...(this.vocab.byLen.get(L) ?? []));
    const m = getCloseMatches(word, cands, 1, 0.78);
    const out = m.length ? m[0] : null;
    this.closeCache.set(word, out);
    return out;
  }

  private wordCost(w: string): number {
    const hit = this.costCache.get(w);
    if (hit !== undefined) return hit;
    const BREAK = 1.6;
    let c: number;
    const r = this.vocab.rank.get(w);
    if (r !== undefined) {
      c = 0.5 + r / 8000.0;
      if (w.length === 1) c += 2.2;
      else if (w.length === 2 && r > 1500) c += 2.5;
      c += BREAK;
    } else {
      const m = w.length >= 4 && w.length <= 9 ? this.close(w) : null;
      c = m ? 2.0 + this.vocab.rank.get(m)! / 8000.0 + 3.2 + BREAK : 4.0 + 1.6 * w.length + BREAK;
    }
    this.costCache.set(w, c);
    return c;
  }

  segment(s: string): string {
    const n = s.length;
    if (!n) return "";
    const cost = [0, ...Array(n).fill(Infinity)];
    const back = Array(n + 1).fill(0);
    for (let i = 1; i <= n; i++) {
      for (let j = Math.max(0, i - 16); j < i; j++) {
        const c = cost[j] + this.wordCost(s.slice(j, i));
        if (c < cost[i]) { cost[i] = c; back[i] = j; }
      }
    }
    const out: string[] = [];
    for (let i = n; i > 0; i = back[i]) out.push(s.slice(back[i], i));
    return out.reverse().join(" ");
  }

  correctWord(w: string): [string, boolean] {
    if (this.vocab.all.has(w) || w.length < 3) return [w, false];
    const m = this.close(w);
    return m ? [m, true] : [w, false];
  }

  suggest(prefix: string, k = 3): string[] {
    const p = prefix.toUpperCase().replace(/[^A-Z]/g, "");
    if (p.length < 2) return [];
    const out: string[] = [];
    for (const w of this.vocab.words) {
      if (w.startsWith(p) && w !== p) {
        out.push(w);
        if (out.length >= k) break;
      }
    }
    return out;
  }

  private detectLang(words: string[]): "French" | "English" | null {
    let fr = 0, en = 0;
    for (const w of words) {
      const u = w.toUpperCase();
      if (this.vocab.fr.has(u) && !this.vocab.en.has(u)) fr++;
      if (this.vocab.en.has(u) && !this.vocab.fr.has(u)) en++;
    }
    return fr > en ? "French" : en > fr ? "English" : null;
  }

  interpret(raw: string): Interpretation {
    const journal: string[] = [];
    const s = raw.replace(/[^A-Za-z ]/g, "").toUpperCase().trim();
    if (!s) return { text: "", journal: ["(nothing to interpret)"] };
    const t = collapseRepeats(s);
    if (t !== s) journal.push(`Removed repeats: ${s} -> ${t}`);

    const words: string[] = [];
    const expandOrCorrect = (w: string) => {
      if (Object.hasOwn(ABBREV, w)) {
        journal.push(`Shorthand: ${w} -> ${ABBREV[w]}`);
        words.push(...ABBREV[w].split(" "));
        return;
      }
      const [cw, changed] = this.correctWord(w);
      if (changed) journal.push(`Fixed typo: ${w} -> ${cw}`);
      words.push(cw);
    };

    for (const chunk of t.split(/\s+/).filter(Boolean)) {
      if (Object.hasOwn(ABBREV, chunk)) {
        journal.push(`Shorthand: ${chunk} -> ${ABBREV[chunk]}`);
        words.push(...ABBREV[chunk].split(" "));
        continue;
      }
      if (this.vocab.all.has(chunk)) { words.push(chunk); continue; }
      const seg = this.segment(chunk);
      if (seg !== chunk) journal.push(`Split words: ${chunk} -> ${seg}`);
      for (const w of seg.split(" ")) expandOrCorrect(w);
    }

    const lang = this.detectLang(words);
    if (lang) journal.push(`Language: ${lang}`);
    let out = words.map((w) => w.toLowerCase());
    if (lang === "English") out = out.map((w) => (w === "i" ? "I" : w));
    let text = out.join(" ").trim();
    text = text ? text[0].toUpperCase() + text.slice(1) : text;
    if (!journal.length) journal.push("Already clean, nothing to change.");
    return { text, journal };
  }
}

export function collapseRepeats(s: string): string {
  return s.replace(/(.)\1{2,}/g, "$1$1");
}

/** Watches the letter stream and interprets the sentence on its own after a pause. */
export class InterpretingAgent {
  auto = true;
  pauseS = 5;
  interpretation = "";
  journal: string[] = [];
  suggestions: string[] = [];
  private lastHandT = performance.now() / 1000;
  private lastInterpretedRaw: string | null = null;

  constructor(private agent: Agent) {}

  observe(raw: string, handPresent: boolean, now = performance.now() / 1000) {
    if (!raw.trim()) this.lastInterpretedRaw = null;
    if (handPresent) {
      this.lastHandT = now;
      const last = raw ? raw.split(" ").pop() ?? "" : "";
      this.suggestions = this.agent.suggest(last);
    } else if (this.auto && now - this.lastHandT >= this.pauseS && raw.trim() && raw !== this.lastInterpretedRaw) {
      this.setResult(this.agent.interpret(raw));
      this.lastInterpretedRaw = raw;
    }
  }

  interpretNow(raw: string) {
    this.setResult(this.agent.interpret(raw));
    this.lastInterpretedRaw = raw;
    return this.interpretation;
  }

  /** Take the current interpretation and wait for the next sentence (conversation mode). */
  consume(): string {
    const out = this.interpretation;
    this.interpretation = "";
    this.journal = [];
    return out;
  }

  private setResult(r: Interpretation) {
    this.interpretation = r.text;
    this.journal = r.journal;
  }
}
