import { useEffect, useRef } from "react";

// 21 hand landmarks of an open hand, drawn in chrome; fingers ripple gently (static if reduced motion).
const BASE = [[120, 250], [88, 228], [66, 200], [52, 172], [42, 148], [92, 160], [86, 116], [82, 88], [79, 62],
  [120, 154], [120, 106], [120, 74], [120, 46], [146, 160], [152, 114], [155, 85], [158, 60], [170, 172], [181, 140], [187, 118], [192, 96]];
const BONES = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [5, 6], [6, 7], [7, 8], [5, 9], [9, 10], [10, 11], [11, 12],
  [9, 13], [13, 14], [14, 15], [15, 16], [13, 17], [17, 18], [18, 19], [19, 20], [0, 17]];
const TIPS = new Set([4, 8, 12, 16, 20]);

export function HandArt() {
  const lines = useRef<(SVGLineElement | null)[]>([]);
  const dots = useRef<(SVGCircleElement | null)[]>([]);

  useEffect(() => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let raf = 0;
    const frame = (t: number) => {
      const P = BASE.map(([x, y], i) => {
        const finger = i === 0 ? -1 : Math.floor((i - 1) / 4), seg = i === 0 ? 0 : (i - 1) % 4;
        const wave = finger < 0 ? 0 : Math.sin(t / 650 - finger * 0.7) * seg * 2.4;
        return [x + wave * 0.4 + Math.sin(t / 1800) * 3, y + wave + Math.cos(t / 2100) * 4];
      });
      BONES.forEach(([a, b], k) => {
        const l = lines.current[k];
        l?.setAttribute("x1", String(P[a][0])); l?.setAttribute("y1", String(P[a][1]));
        l?.setAttribute("x2", String(P[b][0])); l?.setAttribute("y2", String(P[b][1]));
      });
      P.forEach(([x, y], i) => { dots.current[i]?.setAttribute("cx", String(x)); dots.current[i]?.setAttribute("cy", String(y)); });
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <svg className="hand-art" viewBox="0 0 240 280" role="img" aria-label="Hand skeleton, as the camera sees it">
      <defs>
        <linearGradient id="chrome" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#CFD3E6" /><stop offset=".5" stopColor="#FFFFFF" /><stop offset="1" stopColor="#AEB4CE" />
        </linearGradient>
        <radialGradient id="halo" cx="50%" cy="55%" r="50%">
          <stop offset="0" stopColor="#F6D8FF" stopOpacity=".55" /><stop offset=".55" stopColor="#D8F3FF" stopOpacity=".35" />
          <stop offset="1" stopColor="#E7E9F1" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx="120" cy="150" r="120" fill="url(#halo)" />
      {BONES.map(([a, b], k) => (
        <line key={k} ref={(el) => { lines.current[k] = el; }} x1={BASE[a][0]} y1={BASE[a][1]} x2={BASE[b][0]} y2={BASE[b][1]}
          stroke="url(#chrome)" strokeWidth={6} strokeLinecap="round" />
      ))}
      {BASE.map(([x, y], i) => (
        <circle key={i} ref={(el) => { dots.current[i] = el; }} cx={x} cy={y} r={TIPS.has(i) ? 6 : 4.2}
          fill={TIPS.has(i) ? "#0E1330" : "#FFFFFF"} stroke="#0E1330" strokeWidth={1.4} />
      ))}
    </svg>
  );
}
