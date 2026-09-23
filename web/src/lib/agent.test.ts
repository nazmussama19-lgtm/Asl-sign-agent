import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { Agent, InterpretingAgent, Vocabulary, collapseRepeats } from "./agent";
import fixtures from "./__fixtures__/agent.json";

const dir = resolve(__dirname, "../../public/vocab");
const vocab = Vocabulary.fromText(readFileSync(`${dir}/vocab_fr.txt`, "utf8"), readFileSync(`${dir}/vocab_en.txt`, "utf8"));
const agent = new Agent(vocab);

describe("agent", () => {
  it("reads the classic examples", () => {
    const cases: Record<string, string> = {
      HELLLO: "Hello", HELLOWORLD: "Hello world", THAANKYOU: "Thank you", "ILOVE U": "I love you",
      "SEE U TMRW": "See you tomorrow", MERCIBEAUCOUP: "Merci beaucoup", CAVABIEN: "Ca va bien",
    };
    for (const [raw, expected] of Object.entries(cases)) expect(agent.interpret(raw).text).toBe(expected);
    expect(collapseRepeats("HELLLLO")).toBe("HELLO");
    expect(agent.suggest("HEL")).toContain("HELLO");
  });

  it("gives exactly the same result as the Python agent", { timeout: 60000 }, () => {
    for (const c of fixtures.interpret) {
      const got = agent.interpret(c.raw);
      expect({ raw: c.raw, text: got.text, journal: got.journal }).toEqual(c);
    }
    for (const s of fixtures.suggest) expect(agent.suggest(s.prefix)).toEqual(s.out);
  });

  it("interprets on its own after a pause", () => {
    const ia = new InterpretingAgent(agent);
    ia.pauseS = 5;
    ia.observe("HELLOWORLD", true, 100);
    ia.observe("HELLOWORLD", false, 103);
    expect(ia.interpretation).toBe("");
    ia.observe("HELLOWORLD", false, 106);
    expect(ia.interpretation).toBe("Hello world");
    expect(ia.consume()).toBe("Hello world");
    ia.observe("HELLOWORLD", false, 110);          // same raw text: no second interpretation
    expect(ia.interpretation).toBe("");
  });
});
