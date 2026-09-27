import { describe, expect, it } from "vitest";
import { analysisDue } from "./rate";

function analysed(cameraFps: number, seconds = 2) {
  let last = -Infinity, n = 0;
  for (let f = 0; f < seconds * cameraFps; f++) {
    const t = (f * 1000) / cameraFps;
    if (analysisDue(t, last)) { last = t; n++; }
  }
  return n / seconds;
}

describe("analysis rate", () => {
  it("reads a 30 fps camera at 15 frames per second", () => {
    expect(analysed(30)).toBe(15);
  });

  it("reads a 60 fps camera at 15 frames per second", () => {
    expect(analysed(60)).toBe(15);
  });

  it("keeps every frame of a camera already at 15 fps or less", () => {
    expect(analysed(15)).toBe(15);
    expect(analysed(10)).toBe(10);
  });
});
