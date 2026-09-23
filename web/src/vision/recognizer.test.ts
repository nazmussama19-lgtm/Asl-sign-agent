import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { Agent, Vocabulary } from "../lib/agent";
import { Model, type Manifest } from "../lib/nn";
import { Recognizer } from "./recognizer";

const pub = resolve(__dirname, "../../public");
function model(name: string) {
  const manifest = JSON.parse(readFileSync(`${pub}/models/${name}.json`, "utf8")) as Manifest;
  const buf = readFileSync(`${pub}/models/${name}.bin`);
  return new Model(manifest, new Float32Array(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength)));
}
const models = {
  letters: model("letters"), words: model("words"),
  letterLabels: JSON.parse(readFileSync(`${pub}/models/letters_labels.json`, "utf8")) as string[],
  wordLabels: JSON.parse(readFileSync(`${pub}/models/words_labels.json`, "utf8")) as string[],
};
const agent = new Agent(Vocabulary.fromText(readFileSync(`${pub}/vocab/vocab_fr.txt`, "utf8"), readFileSync(`${pub}/vocab/vocab_en.txt`, "utf8")));

// An open hand sliding sideways: enough motion for the gesture detector
const hand = (dx: number) => ({ label: "Right" as const, landmarks: Array.from({ length: 21 }, (_, i) => [0.4 + dx + (i % 5) * 0.02, 0.3 + Math.floor(i / 5) * 0.05, 0]) });

function movingFrames(r: Recognizer) {
  let moving = false;
  for (let f = 0; f < 10; f++) moving = r.process([hand(f * 0.04)]).moving || moving;
  return moving;
}

describe("recognizer", () => {
  it("tracks motion for word signs even when J/Z detection is off", () => {
    const r = new Recognizer(models, agent);
    r.dynEnabled = false;
    r.wordsEnabled = true;
    expect(movingFrames(r)).toBe(true);
  });

  it("does not track motion when both J/Z and word signs are off", () => {
    const r = new Recognizer(models, agent);
    r.dynEnabled = false;
    r.wordsEnabled = false;
    expect(movingFrames(r)).toBe(false);
  });
});
