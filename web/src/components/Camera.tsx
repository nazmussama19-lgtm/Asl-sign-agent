import { useEffect, useRef, useState, type ReactNode } from "react";
import type { HandLandmarker } from "@mediapipe/tasks-vision";
import { createHandTracker, toHands, type Hand } from "../vision/handTracker";

const BONES = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [5, 6], [6, 7], [7, 8], [5, 9], [9, 10], [10, 11], [11, 12],
  [9, 13], [13, 14], [14, 15], [15, 16], [13, 17], [17, 18], [18, 19], [19, 20], [0, 17]];
const TIPS = new Set([4, 8, 12, 16, 20]);

interface Props {
  numHands: number;
  onHands: (hands: Hand[]) => void;
  overlay?: ReactNode;
  caption?: string;
}

type Status = "idle" | "starting" | "running" | "error";

/** Webcam + in-browser hand tracking. Frames are analysed locally and never uploaded. */
export function Camera({ numHands, onHands, overlay, caption }: Props) {
  const video = useRef<HTMLVideoElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const tracker = useRef<HandLandmarker | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const handler = useRef(onHands);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState("");
  handler.current = onHands;

  useEffect(() => { tracker.current?.setOptions({ numHands }).catch(() => undefined); }, [numHands]);

  useEffect(() => {
    if (status !== "running") return;
    let raf = 0, lastTime = -1;
    const loop = () => {
      raf = requestAnimationFrame(loop);
      const v = video.current, c = canvas.current, t = tracker.current;
      if (!v || !c || !t || v.readyState < 2 || v.currentTime === lastTime) return;
      lastTime = v.currentTime;
      const result = t.detectForVideo(v, performance.now());
      const W = v.videoWidth, H = v.videoHeight;
      if (c.width !== W || c.height !== H) { c.width = W; c.height = H; }
      const ctx = c.getContext("2d")!;
      ctx.clearRect(0, 0, W, H);
      for (const lms of result.landmarks) {
        const P = lms.map((p) => [(1 - p.x) * W, p.y * H]);          // the video is shown mirrored
        ctx.lineCap = "round";
        ctx.strokeStyle = "rgba(255,255,255,0.92)";
        ctx.lineWidth = Math.max(3, W / 180);
        for (const [a, b] of BONES) { ctx.beginPath(); ctx.moveTo(P[a][0], P[a][1]); ctx.lineTo(P[b][0], P[b][1]); ctx.stroke(); }
        P.forEach(([x, y], i) => {
          ctx.beginPath();
          ctx.arc(x, y, TIPS.has(i) ? W / 110 : W / 160, 0, Math.PI * 2);
          ctx.fillStyle = TIPS.has(i) ? "#F6D8FF" : "#0E1330";
          ctx.fill();
          ctx.lineWidth = 2;
          ctx.strokeStyle = "#fff";
          ctx.stroke();
        });
      }
      handler.current(toHands(result, W, H));
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [status]);

  useEffect(() => () => stop(), []);

  async function start() {
    setStatus("starting");
    setError("");
    try {
      const [media, tr] = await Promise.all([
        navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" }, audio: false }),
        tracker.current ? Promise.resolve(tracker.current) : createHandTracker(numHands),
      ]);
      stream.current = media;
      tracker.current = tr;
      video.current!.srcObject = media;
      await video.current!.play();
      setStatus("running");
    } catch (e) {
      const name = (e as Error)?.name;
      setError(name === "NotAllowedError"
        ? "Camera access was blocked. Allow the camera in your browser's address bar, then try again."
        : name === "NotFoundError"
          ? "No camera was found on this device."
          : "The camera or the hand tracking could not start. Reload the page and try again.");
      stop();
      setStatus("error");
    }
  }

  function stop() {
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    if (video.current) video.current.srcObject = null;
    canvas.current?.getContext("2d")?.clearRect(0, 0, canvas.current.width, canvas.current.height);
    setStatus((s) => (s === "error" ? s : "idle"));
    handler.current([]);
  }

  return (
    <div className="stack">
      <div className="stage">
        <video ref={video} playsInline muted />
        <canvas ref={canvas} />
        {status === "running" && overlay && <div className="overlay">{overlay}</div>}
        {status === "running" && caption !== undefined && <div className="bar">{caption}</div>}
        {status !== "running" && (
          <div className="idle">
            <div>
              <p>{status === "error" ? error : status === "starting" ? "Starting the camera and the hand tracking…" :
                "Your video is analysed on this computer and is never uploaded."}</p>
              {status !== "starting" && <button className="btn primary" onClick={start}>Start the camera</button>}
            </div>
          </div>
        )}
      </div>
      {status === "running" && (
        <div className="btn-row"><button className="btn small" onClick={stop}>Stop the camera</button></div>
      )}
    </div>
  );
}
