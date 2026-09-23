import { useEffect, useMemo, useState } from "react";
import { GIFEncoder, applyPalette, quantize } from "gifenc";
import { Keycaps } from "../components/Keycaps";
import { translate } from "../lib/conversation";
import { WORD_TO_SIGN, cleanWord, letterImage, signVideo } from "../lib/signs";

type Item = { type: "letter"; ch: string } | { type: "space" };

function buildItems(sentence: string): Item[] {
  const words = sentence.split(/\s+/).map(cleanWord).filter(Boolean);
  return words.flatMap((w, i) => [...[...w].map((ch) => ({ type: "letter" as const, ch })), ...(i < words.length - 1 ? [{ type: "space" as const }] : [])]);
}

function wordLinks(sentence: string): [string, string][] {
  const seen = new Set<string>();
  const out: [string, string][] = [];
  for (const w of sentence.split(/\s+/).map(cleanWord)) {
    const sign = WORD_TO_SIGN[w];
    if (sign && !seen.has(sign)) { seen.add(sign); out.push([w, sign]); }
  }
  return out;
}

export default function TextToSign() {
  const [text, setText] = useState("HELLO MY FRIEND");
  const [lang, setLang] = useState<"en" | "fr">("en");
  const [doTranslate, setDoTranslate] = useState(false);
  const [speed, setSpeed] = useState(0.8);
  const [shown, setShown] = useState("");
  const [translated, setTranslated] = useState<string | null>(null);
  const [warning, setWarning] = useState("");
  const [idx, setIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [gif, setGif] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const items = useMemo(() => buildItems(shown), [shown]);
  const links = useMemo(() => wordLinks(shown), [shown]);

  useEffect(() => {
    if (!playing || !items.length) return;
    const t = setTimeout(() => {
      if (idx + 1 < items.length) setIdx(idx + 1); else setPlaying(false);
    }, speed * 1000);
    return () => clearTimeout(t);
  }, [playing, idx, items, speed]);

  async function show() {
    setWarning(""); setTranslated(null); setGif(null);
    let final = text;
    if (doTranslate && text.trim()) {
      const out = await translate(text, lang === "en" ? "fr" : "en");
      if (out) { final = out; setTranslated(out); } else setWarning("Translation is unavailable right now: showing the original text.");
    }
    setShown(final); setIdx(0); setPlaying(true);
  }

  async function exportGif() {
    setBusy(true);
    try {
      const W = 320, H = 352, enc = GIFEncoder();
      const canvas = document.createElement("canvas");
      canvas.width = W; canvas.height = H;
      const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
      const cache = new Map<string, HTMLImageElement>();
      const load = (src: string) => cache.get(src) ?? new Promise<HTMLImageElement>((ok, ko) => {
        const img = new Image(); img.onload = () => { cache.set(src, img); ok(img); }; img.onerror = ko; img.src = src;
      });
      for (const it of items) {
        ctx.fillStyle = "#F4F5FA"; ctx.fillRect(0, 0, W, H);
        if (it.type === "letter") {
          const img = await load(letterImage(it.ch));
          const s = Math.min(290 / img.width, 290 / img.height);
          ctx.drawImage(img, (W - img.width * s) / 2, (320 - img.height * s) / 2, img.width * s, img.height * s);
        }
        ctx.fillStyle = "#0E1330"; ctx.fillRect(0, 320, W, 32);
        ctx.fillStyle = "#fff"; ctx.font = "600 16px 'DM Sans', sans-serif";
        ctx.fillText(it.type === "letter" ? it.ch : "Space", 12, 342);
        const { data } = ctx.getImageData(0, 0, W, H);
        const palette = quantize(data, 64);
        enc.writeFrame(applyPalette(data, palette), W, H, { palette, delay: Math.round(speed * (it.type === "space" ? 700 : 1000)) });
      }
      enc.finish();
      setGif(URL.createObjectURL(new Blob([enc.bytes()], { type: "image/gif" })));
    } finally {
      setBusy(false);
    }
  }

  const it = items[Math.min(idx, items.length - 1)];
  const letterIdx = items.slice(0, idx + 1).filter((x) => x.type === "letter").length - 1;

  return (
    <>
      <h1 className="page-title">Text to sign</h1>
      <p className="page-sub">Type a sentence and watch it fingerspelled, letter by letter. Words that have their own sign link to videos of real signers.</p>

      <div className="grid-2">
        <label className="field">Your text
          <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Type a sentence" />
        </label>
        <div className="stack">
          <label className="field">Text language
            <select value={lang} onChange={(e) => setLang(e.target.value as "en" | "fr")}><option value="en">English</option><option value="fr">French</option></select>
          </label>
          <label className="check"><input type="checkbox" checked={doTranslate} onChange={(e) => setDoTranslate(e.target.checked)} />
            Translate to {lang === "en" ? "French" : "English"} first</label>
          <label className="field"><span style={{ display: "flex", justifyContent: "space-between" }}>Speed (seconds per letter)<b>{speed.toFixed(1)}</b></span>
            <input type="range" min={0.3} max={2} step={0.1} value={speed} onChange={(e) => setSpeed(Number(e.target.value))} />
          </label>
        </div>
      </div>
      <div className="btn-row" style={{ margin: "18px 0 28px" }}>
        <button className="btn primary" onClick={show} disabled={!text.trim()}>Show in sign language</button>
      </div>
      {warning && <p className="feed err">{warning}</p>}

      {items.length > 0 && it && (
        <div className="grid-2">
          <div className="stack">
            {translated && <p className="muted">Translation: {translated}</p>}
            <div className="panel player">
              {it.type === "letter" ? <img src={letterImage(it.ch)} alt={`ASL sign for ${it.ch}`} /> : <div className="readout empty">Space</div>}
              <span className="muted">{it.type === "letter" ? `Letter ${it.ch}` : "Space"}</span>
            </div>
            <div className="progress"><div style={{ width: `${((idx + 1) / items.length) * 100}%` }} /></div>
            <Keycaps text={shown.split(/\s+/).map(cleanWord).filter(Boolean).join(" ")} done={Math.max(0, letterIdx)} now={it.type === "letter" ? letterIdx : null} size="sm" />
            <div className="btn-row">
              <button className="btn small" onClick={() => { if (!playing && idx >= items.length - 1) setIdx(0); setPlaying(!playing); }}>{playing ? "Pause" : "Play"}</button>
              <button className="btn small" onClick={() => { setIdx(0); setPlaying(true); }}>Restart</button>
            </div>
          </div>
          <div className="stack">
            {links.length > 0 && (
              <div className="panel">
                <p className="panel-label">Word signs in this sentence</p>
                <p className="muted">These words have their own sign in ASL. They are spelled here; watch the real sign.</p>
                <ul>{links.map(([w, sign]) => <li key={sign}><b>{w}</b>: <a href={signVideo(sign)} target="_blank" rel="noreferrer">watch real signers</a></li>)}</ul>
              </div>
            )}
            <div className="panel stack">
              <p className="panel-label">Export</p>
              <p className="muted">Download the sentence as an animated GIF to share it.</p>
              <div className="btn-row"><button className="btn small" onClick={exportGif} disabled={busy}>{busy ? "Creating…" : "Create GIF"}</button></div>
              {gif && <>
                <img src={gif} alt="Your sentence in sign language" style={{ width: 220, borderRadius: 12 }} />
                <a className="btn small" href={gif} download="signs.gif">Download GIF</a>
              </>}
            </div>
          </div>
        </div>
      )}
      <p className="muted" style={{ marginTop: 40 }}>Letters: public-domain drawings from Wikimedia Commons (wpclipart.com). J and Z involve a movement: the drawing shows the starting pose.</p>
    </>
  );
}
