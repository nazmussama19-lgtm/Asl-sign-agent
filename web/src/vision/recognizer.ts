// Per-frame pipeline of the Sign to Text page: port of ASLProcessor.recv in views/sign_to_text.py.
import { InterpretingAgent, type Agent } from "../lib/agent";
import { DynamicDetector, GestureEpisode, SentenceBuilder, buildFrameFeatures, isThumbsUp, normalizeLandmarks, resampleSequence } from "../lib/core";
import type { Model } from "../lib/nn";
import { CustomSigns, PersonalLetters } from "../lib/personal";
import type { Hand } from "./handTracker";

export interface Models { letters: Model; letterLabels: string[]; words: Model; wordLabels: string[] }

export interface FrameState {
  sentence: string;
  handPresent: boolean;
  top: { label: string; conf: number }[];      // best 3 letters for the current frame
  moving: boolean;
  flash: string | null;                         // "Word sign: HELLO", "Accepted: HELLO", ...
  capture: string | null;                       // instructions while recording examples
}

const now = () => performance.now() / 1000;
const argsort = (p: Float32Array) => [...p.keys()].sort((a, b) => p[b] - p[a]);

export class Recognizer {
  builder = new SentenceBuilder();
  detector = new DynamicDetector();
  agent: InterpretingAgent;
  personal = new PersonalLetters();
  custom = new CustomSigns();
  dynEnabled = true;
  wordsEnabled = false;
  personalEnabled = true;
  customRecord: { name: string; remaining: number } | null = null;
  personalCapture: { letter: string; remaining: number; next: number } | null = null;

  private episode = new GestureEpisode(12);
  private thumbFrames = 0;
  private lastAccept = 0;
  private flash: { text: string; t: number } | null = null;

  constructor(private models: Models, agent: Agent) {
    this.agent = new InterpretingAgent(agent);
  }

  process(hands: Hand[]): FrameState {
    const hand = hands[0] ?? null;
    let label = "nothing", conf = 0, moving = false, dynLetter: string | null = null;
    let top: FrameState["top"] = [];

    let twoHand: Float32Array | null = null;
    if (this.wordsEnabled && hands.length) {
      const left = hands.find((h) => h.label === "Left")?.landmarks ?? null;
      const right = hands.find((h) => h.label === "Right")?.landmarks ?? null;
      twoHand = buildFrameFeatures(left, right);
    }

    if (hand) {
      const feats = normalizeLandmarks(hand.landmarks);
      const pred = this.models.letters.predict(feats);
      const order = argsort(pred);
      top = order.slice(0, 3).map((i) => ({ label: this.models.letterLabels[i], conf: pred[i] }));
      label = top[0].label;
      conf = top[0].conf;
      if (this.personalEnabled) ({ label, conf } = this.personal.refine(feats, label, conf));
      if (this.personalCapture && now() >= this.personalCapture.next && conf > 0) {
        this.personal.add(this.personalCapture.letter, feats);
        const remaining = this.personalCapture.remaining - 1;
        this.personalCapture = remaining > 0 ? { ...this.personalCapture, remaining, next: now() + 0.6 } : null;
      }
      // Motion tracking serves J/Z and word signs; J/Z letters are only written when J/Z detection is on
      if (this.dynEnabled || this.wordsEnabled) ({ moving, letter: dynLetter } = this.detector.update(hand.landmarks, conf >= 0.6 ? label : null));
      if (!this.dynEnabled) dynLetter = null;
    }

    // Thumbs up: accept the first suggestion
    const thumbs = hand !== null && isThumbsUp(hand.landmarks);
    this.thumbFrames = thumbs ? this.thumbFrames + 1 : 0;
    if (this.thumbFrames >= 8 && now() - this.lastAccept > 1.5) {
      const s = this.agent.suggestions;
      if (s.length) {
        this.builder.acceptWord(s[0]);
        this.flash = { text: "Accepted: " + s[0], t: now() };
        this.lastAccept = now();
      }
      this.thumbFrames = 0;
    }

    let commitLabel = label;
    if (thumbs || (this.dynEnabled && (label === "J" || label === "Z"))) commitLabel = "nothing";
    if ((this.dynEnabled || this.wordsEnabled) && moving) this.builder.update("nothing", 0);   // no letters mid-gesture
    else this.builder.update(commitLabel, conf);

    if (this.wordsEnabled) {
      const done = this.episode.step(moving && hand !== null, twoHand ?? new Float32Array(126));
      if (done) {
        if (this.customRecord) {
          const n = this.custom.add(this.customRecord.name, done);
          const remaining = this.customRecord.remaining - 1;
          this.flash = { text: `Saved ${this.customRecord.name} (${n})`, t: now() };
          this.customRecord = remaining > 0 ? { ...this.customRecord, remaining } : null;
          dynLetter = null;
        } else {
          let word = this.custom.match(done).name;
          if (!word) {
            const p = this.models.words.predict(resampleSequence(done), 32);
            const i = argsort(p)[0];
            if (p[i] >= 0.7) word = this.models.wordLabels[i];
          }
          if (word) {
            this.builder.commitWord(word);
            this.flash = { text: "Word sign: " + word.toUpperCase(), t: now() };
            dynLetter = null;          // a word sign wins over J/Z
          }
        }
      }
    }
    if (dynLetter) this.builder.commit(dynLetter);

    const sentence = this.builder.get();
    this.agent.observe(sentence, hand !== null);

    const capture = this.customRecord
      ? `Recording "${this.customRecord.name}": do the gesture (${this.customRecord.remaining} left)`
      : this.personalCapture
        ? `Hold the letter ${this.personalCapture.letter} (${this.personalCapture.remaining} examples left)`
        : null;
    const flash = this.flash && now() - this.flash.t < 1.6 ? this.flash.text : null;
    return { sentence, handPresent: hand !== null, top, moving, flash, capture };
  }
}
