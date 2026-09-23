import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { Model, type Manifest } from "./nn";
import fixtures from "./__fixtures__/models.json";

function loadLocal(name: string): Model {
  const dir = resolve(__dirname, "../../public/models");
  const manifest = JSON.parse(readFileSync(`${dir}/${name}.json`, "utf8")) as Manifest;
  const buf = readFileSync(`${dir}/${name}.bin`);
  const weights = new Float32Array(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
  return new Model(manifest, weights);
}

describe("models match the NumPy reference (itself checked against Keras in CI)", () => {
  for (const [name, steps] of [["letters", 1], ["words", 32]] as const) {
    it(name, () => {
      const model = loadLocal(name);
      for (const { input, output } of (fixtures as Record<string, { input: number[]; output: number[] }[]>)[name]) {
        const got = model.predict(input, steps);
        expect(got.length).toBe(output.length);
        got.forEach((v, i) => expect(v).toBeCloseTo(output[i], 5));
      }
    });
  }
});
