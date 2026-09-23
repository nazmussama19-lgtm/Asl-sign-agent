import { useEffect, useRef, useState } from "react";

interface Props {
  text: string;
  done?: number;          // letters already validated (foil keycaps)
  now?: number | null;    // index of the letter being read (ink keycap)
  size?: "sm" | "md" | "lg";
  label?: string;
}

/** Text as keycaps. A keycap that just became validated gets one sweep of light. */
export function Keycaps({ text, done = 0, now = null, size = "md", label }: Props) {
  const prevDone = useRef(done);
  const [fresh, setFresh] = useState<number[]>([]);

  useEffect(() => {
    if (done > prevDone.current) {
      const added = Array.from({ length: done - prevDone.current }, (_, i) => prevDone.current + i);
      setFresh(added);
      const t = setTimeout(() => setFresh([]), 950);
      prevDone.current = done;
      return () => clearTimeout(t);
    }
    prevDone.current = done;
  }, [done]);

  let idx = 0;
  return (
    <div className={`caps ${size === "md" ? "" : size}`} aria-label={label ?? text} role="img">
      {[...text].map((ch, i) => {
        if (ch === " ") return <span key={i} className="cap gap" />;
        const k = idx++;
        const cls = k < done ? "done" : k === now ? "now" : "";
        return <span key={i} className={`cap ${cls} ${fresh.includes(k) ? "fresh" : ""}`}>{ch}</span>;
      })}
    </div>
  );
}
