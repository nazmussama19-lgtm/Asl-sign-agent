/** What the camera stage shows. Recognition is identical in all three modes:
 *  the models only ever read the 21 hand landmarks, never the pixels around them. */
export type Privacy = "video" | "hand" | "skeleton";

export const PRIVACY_KEY = "asl.privacy";
export const MODES: Privacy[] = ["video", "hand", "skeleton"];

export const PRIVACY_LABEL: Record<Privacy, string> = {
  video: "Video",
  hand: "Hide my face",
  skeleton: "Skeleton only",
};

/** Why you would pick this mode, not just what it does. */
export const PRIVACY_HINT: Record<Privacy, string> = {
  video: "The full camera view. Best when you are alone and want to see yourself sign.",
  hand: "Only your hand stays sharp. Your face and your room are scrambled beyond recognition — for a shared space, a call, or a demo you want to publish.",
  skeleton: "No video at all: just the 21 points the model reads. Nothing of your room is ever drawn on screen.",
};

export function isPrivacy(value: unknown): value is Privacy {
  return typeof value === "string" && (MODES as string[]).includes(value);
}

export type Circle = { x: number; y: number; r: number };

/** How fast the sharp window follows the hand. Lower is smoother and lazier. */
export const SMOOTH = 0.35;

/**
 * The circle kept sharp around one hand, in canvas pixels.
 * `prev` is last frame's circle for the same hand, so the window glides instead of jittering.
 */
export function handWindow(points: [number, number][], w: number, h: number, prev?: Circle): Circle {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const [x, y] of points) {
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  }
  const span = Math.max(maxX - minX, maxY - minY);
  const target: Circle = {
    x: (minX + maxX) / 2,
    y: (minY + maxY) / 2,
    // wide enough to hold the whole hand and a little wrist, never wider than the stage
    r: Math.min(Math.min(w, h) * 0.48, span * 0.95 + w * 0.06),
  };
  if (!prev) return target;
  return {
    x: prev.x + (target.x - prev.x) * SMOOTH,
    y: prev.y + (target.y - prev.y) * SMOOTH,
    r: prev.r + (target.r - prev.r) * SMOOTH,
  };
}
