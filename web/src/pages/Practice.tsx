import { useCallback, useEffect, useRef, useState } from "react";
import { Camera } from "../components/Camera";
import { Keycaps } from "../components/Keycaps";
import { normalizeLandmarks } from "../lib/core";
import { PracticeEngine, loadStats, pickWord, resetStats, samplesCsv, type Level, type Snapshot } from "../lib/practice";
import { useResources } from "../resources";
import type { Hand } from "../vision/handTracker";

export default function Practice() {
  const res = useResources();
  const engine = useRef(new PracticeEngine());
  const current = useRef<{ label: string; conf: number }>({ label: "nothing", conf: 0 });
  const [snap, setSnap] = useState<Snapshot>(engine.current.snapshot());
  const [seen, setSeen] = useState({ label: "", conf: 0 });
  const [mode, setMode] = useState<"words" | "letters">("words");
  const [lang, setLang] = useState<"en" | "fr">("en");
  const [level, setLevel] = useState<Level>("Easy");
  const [stats, setStats] = useState(loadStats());
  const nextAt = useRef<number | null>(null);

  const onHands = useCallback((hands: Hand[]) => {
    if (res.status !== "ready") return;
    const hand = hands[0];
    let label = "nothing", conf = 0, feats: Float32Array | null = null;
    if (hand) {
      feats = normalizeLandmarks(hand.landmarks);
      const p = res.res.models.letters.predict(feats);
      let best = 0;
      for (let i = 1; i < p.length; i++) if (p[i] > p[best]) best = i;
      label = res.res.models.letterLabels[best];
      conf = p[best];
    }
    current.current = { label, conf };
    engine.current.update(label, conf, feats);
  }, [res]);

  const newChallenge = useCallback(() => {
    engine.current.newWord(pickWord(mode, lang, level, engine.current.stats));
    nextAt.current = null;
  }, [mode, lang, level]);

  useEffect(() => {
    const t = setInterval(() => {
      const s = engine.current.snapshot();
      setSnap(s);
      setSeen(current.current);
      if (s.completed) {
        nextAt.current ??= performance.now() + 1600;          // celebrate, then chain the next word
        if (performance.now() >= nextAt.current) { newChallenge(); setStats(loadStats()); }
      }
    }, 120);
    return () => clearInterval(t);
  }, [newChallenge]);

  const ev = snap.lastEvent;
  const recent = ev && performance.now() / 1000 - ev.t < 1.6;
  const target = snap.word && snap.idx < snap.word.length ? snap.word[snap.idx] : "";
  const rows = Object.entries(stats.letters).filter(([, d]) => d.a > 0).map(([L, d]) => [L, d.c / d.a, d.a] as const).sort((a, b) => a[1] - b[1]);
  const confusions = Object.entries(stats.confusion).sort((a, b) => b[1] - a[1]).slice(0, 5);

  function download() {
    const url = URL.createObjectURL(new Blob([samplesCsv()], { type: "text/csv" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: "user_samples.csv" });
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <h1 className="page-title">Practice</h1>
      <p className="page-sub">Spell the word on screen, one letter at a time. Adaptive drills bring back the letters you miss most.</p>

      <div className="btn-row" style={{ marginBottom: 22, alignItems: "end" }}>
        <label className="field">Mode
          <select value={mode} onChange={(e) => setMode(e.target.value as "words" | "letters")}>
            <option value="words">Words</option><option value="letters">Adaptive letters</option>
          </select>
        </label>
        <label className="field">Word language
          <select value={lang} onChange={(e) => setLang(e.target.value as "en" | "fr")}><option value="en">English</option><option value="fr">French</option></select>
        </label>
        <label className="field">Difficulty
          <select value={level} onChange={(e) => setLevel(e.target.value as Level)}>{["Easy", "Medium", "Hard"].map((l) => <option key={l}>{l}</option>)}</select>
        </label>
        <button className="btn primary" onClick={() => { engine.current.newSession(); newChallenge(); }}>Start a new challenge</button>
      </div>

      <div className="grid-2">
        <Camera numHands={1} onHands={onHands}
          overlay={[
            target && !snap.completed ? <span key="t" className="chip dark">Sign: {target}</span> : null,
            seen.conf >= 0.75 ? <span key="s" className="chip">{seen.label} {Math.round(seen.conf * 100)}%</span> : null,
          ]} />
        <div className="panel">
          <div className="score">
            <div><b>{snap.score}</b>points</div>
            <div><b>{snap.streak}</b>streak</div>
            <div><b>{snap.words}</b>words</div>
            <div><b>{Math.round(snap.lpm)}</b>letters / min</div>
            <div><b>{Math.floor(snap.elapsed / 60)}:{String(Math.floor(snap.elapsed % 60)).padStart(2, "0")}</b>time</div>
          </div>
          {snap.word ? <Keycaps text={snap.word} done={snap.idx} now={snap.completed ? null : snap.idx} size="lg" />
            : <p className="muted">Start the camera, then click Start a new challenge.</p>}
          <div className={`feed ${snap.completed || (recent && ev?.kind === "ok") ? "ok" : recent ? "err" : ""}`} aria-live="polite">
            {snap.completed ? "Word complete, +50 points. Next challenge coming up."
              : recent && ev ? (ev.kind === "ok" ? `${ev.letter} is correct.` : `That looked like ${ev.letter}. Aim for ${target}.`) : ""}
          </div>
        </div>
      </div>

      <h2 className="section-title">Your progress</h2>
      <p className="section-sub">Saved in this browser. The adaptive mode uses these numbers to pick your next letters.</p>
      {rows.length === 0 ? <p className="muted">Play a few challenges: your success rate for each letter will show up here.</p> : (
        <div className="grid-2">
          <div className="panel">
            <p className="panel-label">Success rate by letter</p>
            {rows.map(([L, rate, n]) => (
              <div key={L} className="rate"><span className="l">{L}</span><div className="bar"><div style={{ width: `${rate * 100}%` }} /></div>
                <span className="n">{Math.round(rate * 100)}% of {n} tries</span></div>
            ))}
          </div>
          <div className="stack">
            <div className="panel">
              <p className="panel-label">Totals</p>
              <div className="score" style={{ marginBottom: 0 }}>
                <div><b>{stats.totals.words}</b>words completed</div><div><b>{stats.totals.best_streak}</b>best streak</div>
                <div><b>{stats.totals.samples}</b>samples collected</div>
              </div>
            </div>
            {confusions.length > 0 && (
              <div className="panel">
                <p className="panel-label">Letters you mix up most</p>
                <ul className="muted">{confusions.map(([k, v]) => <li key={k}>You aimed for <b>{k.split(">")[0]}</b>, the model saw <b>{k.split(">")[1]}</b> ({v} times)</li>)}</ul>
              </div>
            )}
            <div className="btn-row">
              <button className="btn small" onClick={download}>Download my samples (CSV)</button>
              <button className="btn small" onClick={() => { resetStats(); engine.current.stats = loadStats(); setStats(loadStats()); }}>Reset my statistics</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
