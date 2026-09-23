import { signVideo } from "../lib/signs";

/** A word sign without an animation: the word, and a button to a real signer inside the frame. */
export function WordFace({ word, large = false }: { word: string; large?: boolean }) {
  return (
    <div className={`word-face ${large ? "lg" : ""}`}>
      <span className="w">{word.toUpperCase()}</span>
      <a className="btn small" href={signVideo(word)} target="_blank" rel="noreferrer" aria-label={`Watch a real person sign ${word}`}>
        Watch the sign
      </a>
    </div>
  );
}
