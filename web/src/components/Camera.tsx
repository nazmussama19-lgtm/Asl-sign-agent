import { useEffect, useRef, useState, type ReactNode } from "react";
import type { HandLandmarker } from "@mediapipe/tasks-vision";
import { createHandTracker, toHands, type Hand } from "../vision/handTracker";
import { load, save } from "../lib/storage";
import { handWindow, isPrivacy, MODES, PRIVACY_HINT, PRIVACY_KEY, PRIVACY_LABEL, type Circle, type Privacy } from "../lib/privacy";

const BONES = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [5, 6], [6, 7], [7, 8], [5, 9], [9, 10], [10, 11], [11, 12],
  [9, 13], [13, 14], [14, 15], [15, 16], [13, 17], [17, 18], [18, 19], [19, 20], [0, 17]];
const TIPS = new Set([4, 8, 12, 16, 20]);

const INK = "14, 19, 48";
const TINY_W = 36;   // the frame is redrawn this small, then blown back up: nothing survives

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
  const [privacy, setPrivacy] = useState<Privacy>(() => {
    const stored = load<unknown>(PRIVACY_KEY, "video");
    return isPrivacy(stored) ? stored : "video";
  });
  handler.current = onHands;

  // read inside the render loop without restarting it
  const mode = useRef(privacy);
  mode.current = privacy;
  const tiny = useRef<HTMLCanvasElement | null>(null);
  const layer = useRef<HTMLCanvasElement | null>(null);
  const windows = useRef<Circle[]>([]);

  useEffect(() => { save(PRIVACY_KEY, privacy); }, [privacy]);
  useEffect(() => { tracker.current?.setOptions({ numHands }).catch(() => undefined); }, [numHands]);

  useEffect(() => {
    if (status !== "running") return;
    let raf = 0, lastTime = -1;
    const scratch = (ref: { current: HTMLCanvasElement | null }, w: number, h: number) => {
      if (!ref.current) ref.current = document.createElement("canvas");
      const c = ref.current;
      if (c.width !== w || c.height !== h) { c.width = w; c.height = h; }
      return c;
    };

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
      const points = result.landmarks.map((lms) => lms.map((p) => [(1 - p.x) * W, p.y * H] as [number, number]));
      const mirror = (g: CanvasRenderingContext2D, draw: () => void) => {
        g.save(); g.translate(W, 0); g.scale(-1, 1); draw(); g.restore();
      };

      // The two private modes paint their own background; the <video> underneath stays hidden.
      // Anything unexpected here falls back to the plain video rather than breaking the page.
      if (mode.current !== "video") {
        try {
          if (mode.current === "hand") {
            const small = scratch(tiny, TINY_W, Math.max(1, Math.round((TINY_W * H) / W)));
            small.getContext("2d")!.drawImage(v, 0, 0, small.width, small.height);
            ctx.save();
            ctx.filter = "blur(12px) saturate(0.55)";
            mirror(ctx, () => ctx.drawImage(small, 0, 0, W, H));
            ctx.restore();
            ctx.fillStyle = `rgba(${INK}, 0.42)`;
            ctx.fillRect(0, 0, W, H);
          } else {
            const back = ctx.createRadialGradient(W / 2, H * 0.45, 0, W / 2, H * 0.45, Math.max(W, H) * 0.7);
            back.addColorStop(0, "#161C3E");
            back.addColorStop(1, "#0B0F26");
            ctx.fillStyle = back;
            ctx.fillRect(0, 0, W, H);
          }

          // vignette, in both private modes: it frames the hand and hides the edges of the room
          const vignette = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.25, W / 2, H / 2, Math.max(W, H) * 0.72);
          vignette.addColorStop(0, `rgba(${INK}, 0)`);
          vignette.addColorStop(1, `rgba(${INK}, 0.6)`);
          ctx.fillStyle = vignette;
          ctx.fillRect(0, 0, W, H);

          if (mode.current === "hand" && points.length) {
            const sharp = scratch(layer, W, H);
            const mc = sharp.getContext("2d")!;
            mc.clearRect(0, 0, W, H);
            points.forEach((P, i) => {
              const win = handWindow(P, W, H, windows.current[i]);
              windows.current[i] = win;
              const soft = mc.createRadialGradient(win.x, win.y, win.r * 0.62, win.x, win.y, win.r);
              soft.addColorStop(0, "rgba(255,255,255,1)");
              soft.addColorStop(1, "rgba(255,255,255,0)");
              mc.fillStyle = soft;
              mc.beginPath();
              mc.arc(win.x, win.y, win.r, 0, Math.PI * 2);
              mc.fill();
            });
            windows.current.length = points.length;
            mc.globalCompositeOperation = "source-in";
            mirror(mc, () => mc.drawImage(v, 0, 0, W, H));
            mc.globalCompositeOperation = "source-over";
            ctx.drawImage(sharp, 0, 0);

            // a soft rim, so the hand reads as lit rather than cut out
            for (const win of windows.current) {
              const rim = ctx.createRadialGradient(win.x, win.y, win.r * 0.82, win.x, win.y, win.r * 1.04);
              rim.addColorStop(0, "rgba(246, 216, 255, 0)");
              rim.addColorStop(0.6, "rgba(246, 216, 255, 0.28)");
              rim.addColorStop(1, "rgba(246, 216, 255, 0)");
              ctx.fillStyle = rim;
              ctx.beginPath();
              ctx.arc(win.x, win.y, win.r * 1.04, 0, Math.PI * 2);
              ctx.fill();
            }
          } else if (mode.current !== "hand") {
            windows.current.length = 0;
          }
        } catch {
          windows.current.length = 0;
          setPrivacy("video");
        }
      } else if (windows.current.length) {
        windows.current.length = 0;
      }

      for (const P of points) {
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
    windows.current.length = 0;
    setStatus((s) => (s === "error" ? s : "idle"));
    handler.current([]);
  }

  return (
    <div className="stack">
      <div className={`stage${privacy === "video" ? "" : " covered"}`}>
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
        <div className="privacy">
          <div className="btn-row">
            <div className="seg" role="radiogroup" aria-label="What the camera shows">
              {MODES.map((k) => (
                <button
                  key={k}
                  type="button"
                  role="radio"
                  aria-checked={privacy === k}
                  className={`seg-btn${privacy === k ? " on" : ""}`}
                  onClick={() => setPrivacy(k)}
                >
                  {PRIVACY_LABEL[k]}
                </button>
              ))}
            </div>
            <button className="btn small" onClick={stop}>Stop the camera</button>
          </div>
          <p className="privacy-hint">
            {PRIVACY_HINT[privacy]}
            <span> The models only ever read the 21 points, so recognition is exactly the same in all three.</span>
          </p>
        </div>
      )}
    </div>
  );
}
