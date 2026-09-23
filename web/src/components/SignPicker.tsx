import { useState } from "react";
import { ALPHABET, WORD_SIGNS, letterImage, signVideo } from "../lib/signs";

const TIPS: Record<string, string> = {
  J: "J is a movement: start from the I pose (little finger up) and draw a hook. Keep J/Z detection on.",
  Z: "Z is a movement: draw a Z in the air with your index finger. Keep J/Z detection on.",
};

export function SignPicker() {
  const [choice, setChoice] = useState("A");
  const isWord = choice.length > 1;
  return (
    <div className="grid-2">
      <div className="panel player" style={{ minHeight: 300 }}>
        {isWord ? <div className="sign-card" style={{ width: "100%", border: 0, background: "none" }}><div className="face" style={{ height: 240, fontSize: 30 }}>{choice.toUpperCase()}</div></div>
          : <img src={letterImage(choice)} alt={`ASL sign for ${choice}`} />}
      </div>
      <div className="stack">
        <label className="field">Sign
          <select value={choice} onChange={(e) => setChoice(e.target.value)}>
            <optgroup label="Letters">{ALPHABET.map((l) => <option key={l} value={l}>{l}</option>)}</optgroup>
            <optgroup label="Word signs">{WORD_SIGNS.map((w) => <option key={w} value={w}>{w.toUpperCase()}</option>)}</optgroup>
          </select>
        </label>
        <div className="panel">
          {isWord ? "Word sign: watch real people sign it, then copy the movement. Turn on Word signs in Settings to try it live."
            : TIPS[choice] ?? "Hold the pose steady in front of the camera: the letter is written once it stays stable."}
        </div>
        <a className="btn" href={signVideo(choice)} target="_blank" rel="noreferrer">Watch real signers</a>
      </div>
    </div>
  );
}
