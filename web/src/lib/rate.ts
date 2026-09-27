// The recognition settings (stability over 4 of 5 frames, motion over 8 frames, word gestures of at
// least 12 frames) were tuned on the Python app, which read about 15 frames per second. The browser
// tracks the hand at the camera's full rate (often 30 fps): at that pace a letter only had to hold
// for ~0.13 s and passing poses (a hand closing into S looks like M for an instant) got written.
// So the landmarks are drawn on every frame, but handed to the recognition at the Python app's rate.
export const ANALYSIS_FPS = 15;

// A little slack so that a 30 fps camera yields exactly every other frame, not an irregular pattern
const SLACK_MS = 5;

/** True when enough time has passed since the last analysed frame (times in milliseconds). */
export function analysisDue(now: number, last: number, fps = ANALYSIS_FPS): boolean {
  return now - last >= 1000 / fps - SLACK_MS;
}
