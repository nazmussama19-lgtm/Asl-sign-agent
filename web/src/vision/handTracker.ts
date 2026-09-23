// MediaPipe hand tracking in the browser: the video never leaves the visitor's computer.
import { FilesetResolver, HandLandmarker, type HandLandmarkerResult } from "@mediapipe/tasks-vision";
import type { Landmarks } from "../lib/core";

const WASM = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35/wasm";
const MODEL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task";

export interface Hand { landmarks: Landmarks; label: "Left" | "Right" }

export async function createHandTracker(numHands: number): Promise<HandLandmarker> {
  const vision = await FilesetResolver.forVisionTasks(WASM);
  const options = (delegate: "GPU" | "CPU") => ({
    baseOptions: { modelAssetPath: MODEL, delegate },
    runningMode: "VIDEO" as const,
    numHands,
    minHandDetectionConfidence: 0.7,
    minHandPresenceConfidence: 0.7,
    minTrackingConfidence: 0.7,
  });
  try {
    return await HandLandmarker.createFromOptions(vision, options("GPU"));
  } catch {
    return HandLandmarker.createFromOptions(vision, options("CPU"));
  }
}

/**
 * Convert a MediaPipe result to what the Python app saw. The Python app mirrored each frame before
 * tracking, on 4:3 video: x is mirrored, handedness swapped accordingly, and x rescaled so a 16:9
 * camera gives the same hand proportions as a 4:3 one (the models were trained on those).
 */
export function toHands(result: HandLandmarkerResult, width: number, height: number): Hand[] {
  const k = width && height ? width / height / (4 / 3) : 1;
  return result.landmarks.map((lms, i) => {
    const raw = result.handedness[i]?.[0]?.categoryName === "Left" ? "Left" : "Right";
    return {
      landmarks: lms.map((p) => [0.5 + (0.5 - p.x) * k, p.y, p.z * k]),
      label: raw === "Left" ? "Right" : "Left",
    };
  });
}
