import { useState } from "react";
import { ALPHABET, WORD_SIGNS, letterImage, signVideo } from "../lib/signs";
import { WordFace } from "./WordFace";

const TIPS: Record<string, string> = {
  J: "J is a movement: start from the I pose (little finger up) and draw a hook. Turn on Detect J and Z in Settings first.",
  Z: "Z is a movement: draw a Z in the air with your index finger. Turn on Detect J and Z in Settings first.",
};

export function SignPicker() {
  const [choice, setChoice] = useState("A");
  const isWord = choice.length > 1;
  return (
    <div className="grid-2">
      <div className="panel player" style={{ minHeight: 300 }}>
        {isWord ? <WordFace word={choice} large />
          : <img src={letterImage(choice)} alt={`ASL sign for ${choice}`} />}
      </div>
      <div className="stack">
        <label className="field">Sign
          <select value={choice} onChange={(e) => setChoice(e.target.value)}>
            <optgroup label="Letters">{ALPHABET.map((l) => <option key={l} value={l}>{l}</option>)}</optgroup>
            <optgroup label="Word signs (9 in this demo)">{WORD_SIGNS.map((w) => <option key={w} value={w}>{w.toUpperCase()}</option>)}</optgroup>
          </select>
        </label>
        <div className="panel">
          {isWord ? "Word sign: click Watch the sign to see a real person sign it. To try it live, turn on Word signs in Settings (J and Z detection is not needed), make the movement, then hold still. This demo recognizes 9 word signs to stay light and fast."
            : TIPS[choice] ?? "Hold the pose steady in front of the camera: the letter is written once it stays stable."}
        </div>
        {!isWord && <a className="btn" href={signVideo(choice)} target="_blank" rel="noreferrer">Watch real signers</a>}
      </div>
    </div>
  );
}
