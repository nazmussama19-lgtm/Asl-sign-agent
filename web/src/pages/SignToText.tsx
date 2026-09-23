import { useCallback, useEffect, useRef, useState } from "react";
import { Camera } from "../components/Camera";
import { Keycaps } from "../components/Keycaps";
import { SignPicker } from "../components/SignPicker";
import { compare, detectLang, fetchProviders, MAX_CLOUD_REPLIES, respond, speak, type ProviderId, type ProviderInfo, type Reply } from "../lib/conversation";
import { useResources } from "../resources";
import { load, save } from "../lib/storage";
import { Recognizer, type FrameState } from "../vision/recognizer";
import type { Hand } from "../vision/handTracker";

interface Turn { user: string; replies: Reply[] }
const EMPTY: FrameState = { sentence: "", handPresent: false, top: [], moving: false, flash: null, capture: null };
const LETTERS_PERSONAL = "ABCDEFGHIKLMNOPQRSTUVWXY";

export default function SignToText() {
  const res = useResources();
  const rec = useRef<Recognizer | null>(null);
  const frame = useRef<FrameState>(EMPTY);
  const [view, setView] = useState<FrameState>(EMPTY);
  const [agentView, setAgentView] = useState({ text: "", journal: [] as string[], suggestions: [] as string[] });

  // settings
  const [conf, setConf] = useState(0.8);
  const [stab, setStab] = useState(4);
  const [cooldown, setCooldown] = useState(0.6);
  const [dyn, setDyn] = useState(false);          // J/Z motion detection is opt-in
  const [moveSens, setMoveSens] = useState(0.12);
  const [words, setWords] = useState(false);
  const [personalOn, setPersonalOn] = useState(true);
  const [auto, setAuto] = useState(true);
  const [pause, setPause] = useState(5);
  const [convOn, setConvOn] = useState(true);
  const [voice, setVoice] = useState(true);
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [provider, setProvider] = useState<ProviderId>("auto");
  const [compareOn, setCompareOn] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);    // settings sheet on small screens
  const [panelOpen, setPanelOpen] = useState(() => load("asl.settingsPanel", true));   // left panel on desktop
  useEffect(() => save("asl.settingsPanel", panelOpen), [panelOpen]);

  function resetSettings() {
    setConf(0.8); setStab(4); setCooldown(0.6); setDyn(false); setMoveSens(0.12); setWords(false); setPersonalOn(true);
    setAuto(true); setPause(5); setConvOn(true); setVoice(true); setProvider("auto"); setCompareOn(false);
  }

  // conversation
  const [turns, setTurns] = useState<Turn[]>([]);
  const [thinking, setThinking] = useState(false);
  const cloudUsed = useRef(0);

  // personalization
  const [signName, setSignName] = useState("");
  const [letter, setLetter] = useState("A");
  const [, force] = useState(0);

  useEffect(() => { fetchProviders().then(setProviders); }, []);

  if (res.status === "ready" && !rec.current) rec.current = new Recognizer(res.res.models, res.res.agent);

  // settings -> recognizer
  useEffect(() => {
    const r = rec.current;
    if (!r) return;
    Object.assign(r.builder, { confThreshold: conf, stabThreshold: stab, cooldown });
    r.detector.moveThreshold = moveSens;
    r.dynEnabled = dyn;
    r.wordsEnabled = words;
    r.personalEnabled = personalOn;
    r.agent.auto = auto;
    r.agent.pauseS = pause;
  }, [conf, stab, cooldown, dyn, moveSens, words, personalOn, auto, pause, res.status]);

  const onHands = useCallback((hands: Hand[]) => {
    if (rec.current) frame.current = rec.current.process(hands);
  }, []);

  // UI refresh at 10 fps; the camera loop itself runs at full speed
  useEffect(() => {
    const t = setInterval(() => {
      const r = rec.current;
      if (!r) return;
      setView(frame.current);
      setAgentView({ text: r.agent.interpretation, journal: r.agent.journal, suggestions: r.agent.suggestions });
    }, 100);
    return () => clearInterval(t);
  }, []);

  // a new interpretation -> the agent answers
  useEffect(() => {
    const r = rec.current;
    if (!convOn || !r || !agentView.text || thinking || res.status !== "ready") return;
    const userMsg = r.agent.consume();
    if (!userMsg) return;
    const history = turns.map((t) => [t.user, t.replies[0]?.text ?? ""] as [string, string]);
    const allowCloud = cloudUsed.current < MAX_CLOUD_REPLIES;
    setThinking(true);
    (compareOn && allowCloud ? compare(userMsg, history, res.res.vocab) : respond(userMsg, history, provider, res.res.vocab, allowCloud).then((x) => [x]))
      .then((replies) => {
        cloudUsed.current += replies.filter((x) => x.provider !== "Local rules").length;
        setTurns((ts) => [...ts, { user: userMsg, replies }]);
        const main = replies.find((x) => x.text);
        if (voice && main) speak(main.text, main.lang);
        r.builder.clear();
      })
      .finally(() => setThinking(false));
  }, [agentView.text, convOn, thinking, compareOn, provider, voice, turns, res]);

  const r = rec.current;
  const raw = view.sentence;
  const shown = raw.slice(-22);
  const nLetters = shown.replace(/ /g, "").length;
  const chips = [
    view.handPresent && !view.moving && view.top.length > 0 ? (
      <div key="top" className="confidence" aria-label="Top 3 letters and their confidence">
        {view.top.map((t, i) => (
          <div key={i} className={`conf-row ${i === 0 && t.conf >= conf ? "best" : ""}`}>
            <span className="k">{t.label === "space" ? "sp" : t.label}</span>
            <span className="meter"><span style={{ width: `${Math.round(t.conf * 100)}%` }} /></span>
            <span className="p">{Math.round(t.conf * 100)}%</span>
          </div>
        ))}
      </div>
    ) : null,
    view.moving ? <span key="m" className="chip">{words ? "Reading a word sign…" : "Motion (J/Z)"}</span> : null,
    view.flash ? <span key="f" className="chip">{view.flash}</span> : null,
    agentView.suggestions[0] && view.handPresent ? <span key="s" className="chip">Thumbs up = {agentView.suggestions[0]}</span> : null,
    view.capture ? <span key="c" className="chip dark">{view.capture}</span> : null,
  ];

  return (
    <>
      <div className={`workspace ${panelOpen ? "with-panel" : ""}`}>
      <div className="workspace-main">
      <h1 className="page-title">Sign to text</h1>
      <p className="page-sub">Sign in front of the camera. The agent builds the text, interprets it after a pause, and answers you.</p>
      {res.status === "error" && <p className="feed err">The models could not load ({res.message}). Reload the page.</p>}

      <div className="grid-2">
        <div className="stack">
          <Camera numHands={words ? 2 : 1} onHands={onHands} overlay={chips} caption={raw.slice(-40) || " "} />
          <p className="muted">{auto ? `Lower your hand for about ${pause} s and the agent interprets the sentence. Thumbs up accepts the suggested word.`
            : "Automatic interpretation is off: click Interpret when you are done."}{" "}
            {words ? "Word signs are on: make the movement, then hold still." : "To sign whole words (hello, food, home…), turn on Word signs in Settings."}</p>
        </div>

        <div className="stack">
          <div className="panel">
            <p className="panel-label">Letters read live</p>
            {raw.trim() ? <Keycaps text={shown} done={Math.max(0, nLetters - 1)} now={nLetters - 1} size="sm" />
              : <div className="readout empty">{r ? "—" : "Loading the models…"}</div>}
          </div>
          <div className="panel">
            <p className="panel-label">Agent interpretation</p>
            <div className={`readout ${agentView.text ? "" : "empty"}`}>{agentView.text || "—"}</div>
            {agentView.suggestions.length > 0 && <p className="muted">Suggestions: {agentView.suggestions.join(", ")}</p>}
            {agentView.journal.length > 0 && (
              <details className="fold" style={{ marginTop: 10 }}>
                <summary>Agent reasoning</summary>
                <ul className="muted">{agentView.journal.map((l, i) => <li key={i}>{l}</li>)}</ul>
              </details>
            )}
          </div>
          <div className="btn-row">
            <button className="btn small" onClick={() => r?.builder.addSpace()}>Space</button>
            <button className="btn small" onClick={() => r?.builder.delete()}>Delete</button>
            <button className="btn small" onClick={() => r?.builder.clear()}>Clear</button>
            <button className="btn small primary" onClick={() => r && r.agent.interpretNow(r.builder.get())}>Interpret</button>
            <button className="btn small" onClick={() => agentView.text && res.status === "ready" && speak(agentView.text, detectLang(agentView.text, res.res.vocab) === "fr" ? "fr-FR" : "en-US")}>Read out loud</button>
          </div>

        </div>
      </div>

      {convOn && (
        <>
          <h2 className="section-title">Conversation</h2>
          <p className="section-sub">Sign a sentence, then pause: the agent answers and speaks.</p>
          <div className="panel">
            <div className="chat" aria-live="polite">
              {turns.length === 0 && <p className="muted">Your conversation will appear here.</p>}
              {turns.map((t, i) => (
                <div key={i} style={{ display: "contents" }}>
                  <div className="bubble user">{t.user}</div>
                  {t.replies.length > 1 ? (
                    <div className="compare">
                      {t.replies.map((x, j) => (
                        <div key={j} className="bubble bot" style={{ maxWidth: "100%" }}>
                          <b style={{ fontFamily: "var(--display)", fontSize: 13 }}>{x.provider === "groq" ? "Groq" : x.provider === "gemini" ? "Gemini" : x.provider} ({x.model})</b>
                          <div>{x.text || x.note}</div><span className="meta">{x.seconds.toFixed(1)} s</span>
                        </div>
                      ))}
                    </div>
                  ) : t.replies.map((x, j) => (
                    <div key={j} className="bubble bot">{x.text}
                      <span className="meta">{describe(x)}</span>
                    </div>
                  ))}
                </div>
              ))}
              {thinking && <p className="muted">Thinking…</p>}
            </div>
            <div className="btn-row" style={{ marginTop: 12 }}>
              <button className="btn small" onClick={() => setTurns([])}>Clear conversation</button>
            </div>
            {cloudUsed.current >= MAX_CLOUD_REPLIES && <p className="muted">This session reached its {MAX_CLOUD_REPLIES} AI replies: the local rules answer now. Reload the page to start again.</p>}
          </div>
        </>
      )}

      <h2 className="section-title">Personalization</h2>
      <p className="section-sub">Saved in this browser only. Start the camera first.</p>
      <div className="grid-2">
        <div className="panel stack">
          <b style={{ fontFamily: "var(--display)" }}>Create a custom sign (3 gestures)</b>
          <p className="muted">Name your sign, click Record, then do the gesture 3 times with a short pause between each. It is then recognized as a whole word.</p>
          <label className="field">Sign name<input type="text" value={signName} placeholder="STOP" onChange={(e) => setSignName(e.target.value)} /></label>
          <div className="btn-row">
            <button className="btn small" disabled={!words || !signName.trim() || !r}
              onClick={() => { if (r) r.customRecord = { name: signName.trim().toUpperCase(), remaining: 3 }; }}>Record 3 gestures</button>
          </div>
          {!words && <p className="muted">Turn on Word signs in Settings first.</p>}
          {r && Object.keys(r.custom.names()).length > 0 && (
            <div className="btn-row">{Object.entries(r.custom.names()).map(([k, v]) => (
              <button key={k} className="btn small" title="Delete this sign" onClick={() => { r.custom.delete(k); force((n) => n + 1); }}>{k} ({v}) ✕</button>
            ))}</div>
          )}
        </div>
        <div className="panel stack">
          <b style={{ fontFamily: "var(--display)" }}>A letter doesn't work for me (5 examples)</b>
          <p className="muted">Pick the letter, click Record, then hold the pose: 5 examples of your hand correct the model right away.</p>
          <label className="field">Letter
            <select value={letter} onChange={(e) => setLetter(e.target.value)}>{[...LETTERS_PERSONAL].map((l) => <option key={l}>{l}</option>)}</select>
          </label>
          <div className="btn-row">
            <button className="btn small" disabled={!r} onClick={() => { if (r) r.personalCapture = { letter, remaining: 5, next: performance.now() / 1000 + 1 }; }}>Record 5 examples</button>
            {r && Object.keys(r.personal.counts()).length > 0 &&
              <button className="btn small" onClick={() => { r.personal.reset(); force((n) => n + 1); }}>Reset all</button>}
          </div>
          {r && Object.keys(r.personal.counts()).length > 0 &&
            <p className="muted">Your examples: {Object.entries(r.personal.counts()).sort().map(([k, v]) => `${k} (${v})`).join(", ")}</p>}
        </div>
      </div>

      <h2 className="section-title">Learn the signs</h2>
      <p className="section-sub">Pick a letter or a word to see how to sign it.</p>
      <SignPicker />
      </div>

      <aside className={`config panel ${sheetOpen ? "open" : ""}`} aria-label="Settings">
        <div className="config-head">
          <h2>Settings</h2>
          <div className="btn-row">
            <button className="btn small" onClick={resetSettings}>Reset</button>
            <button className="btn small config-hide" onClick={() => setPanelOpen(false)} aria-label="Hide the settings panel">Hide</button>
            <button className="btn small config-close" onClick={() => setSheetOpen(false)}>Done</button>
          </div>
        </div>
        <div className="settings">
              <h3>Recognition</h3>
              <Slider label="Confidence threshold" hint="A letter is only accepted above this confidence." value={conf} min={0.5} max={0.99} step={0.01} onChange={setConf} />
              <Slider label="Stability (frames)" hint="Frames that must agree before a letter is written." value={stab} min={2} max={8} step={1} onChange={setStab} />
              <Slider label="Repeat delay (s)" hint="Minimum time between two letters." value={cooldown} min={0.2} max={1.5} step={0.1} onChange={setCooldown} />
              <Check label="Detect J and Z (motion)" value={dyn} onChange={setDyn} hint="J and Z are movements: turn this on to spell them." />
              <Slider label="Motion sensitivity" value={moveSens} min={0.05} max={0.3} step={0.01} onChange={setMoveSens} />
              <Check label="Word signs (9 whole words in this demo)" value={words} onChange={setWords}
                hint="Sign hello, food, home… with one movement, then hold still: the word is written. J and Z detection is not needed." />
              <Check label="Use my letter examples" value={personalOn} onChange={setPersonalOn} />
              <h3>Agent</h3>
              <Check label="Interpret automatically" value={auto} onChange={setAuto} />
              <Slider label="Pause before interpreting (s)" value={pause} min={1} max={8} step={0.5} onChange={setPause} />
              <h3>Conversation</h3>
              <Check label="Reply to my sentences" value={convOn} onChange={setConvOn} />
              <Check label="Read replies out loud" value={voice} onChange={setVoice} />
              <label className="field">AI model
                <select value={provider} onChange={(e) => setProvider(e.target.value as ProviderId)}>
                  <option value="auto">Auto (best available)</option>
                  {providers.map((p) => <option key={p.id} value={p.id}>{p.label} ({p.model})</option>)}
                </select>
                <span className="hint">{providers.length ? "Auto tries Groq, then Groq (fast), then Gemini." : "No AI is configured here: the local rules answer."}</span>
              </label>
              <Check label="Compare Groq and Gemini side by side" value={compareOn} onChange={setCompareOn}
                disabled={!(providers.some((p) => p.id === "groq") && providers.some((p) => p.id === "gemini"))} />
        </div>
      </aside>
      <button className="btn primary config-toggle" onClick={() => setSheetOpen(true)}>Settings</button>
      {!panelOpen && <button className="btn config-tab" onClick={() => setPanelOpen(true)} aria-label="Show the settings panel">Settings</button>}
      </div>
    </>
  );
}

function describe(x: Reply) {
  const name = x.provider === "groq" ? "Groq" : x.provider === "groq_fast" ? "Groq (fast)" : x.provider === "gemini" ? "Gemini" : x.provider;
  const base = `Answered by ${name}${x.model ? ` (${x.model})` : ""}${x.seconds ? ` in ${x.seconds.toFixed(1)} s` : ""}`;
  return x.note ? `${base}. ${x.note}` : base;
}

function Slider({ label, hint, value, min, max, step, onChange }: { label: string; hint?: string; value: number; min: number; max: number; step: number; onChange: (v: number) => void }) {
  return (
    <label className="field">
      <span style={{ display: "flex", justifyContent: "space-between" }}>{label}<b>{step < 1 ? value.toFixed(2) : value}</b></span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} />
      {hint && <span className="hint">{hint}</span>}
    </label>
  );
}

function Check({ label, value, onChange, disabled, hint }: { label: string; value: boolean; onChange: (v: boolean) => void; disabled?: boolean; hint?: string }) {
  return (
    <div className="field">
      <label className="check" style={disabled ? { opacity: 0.5 } : undefined}>
        <input type="checkbox" checked={value} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />{label}
      </label>
      {hint && <span className="hint" style={{ paddingLeft: 27 }}>{hint}</span>}
    </div>
  );
}
