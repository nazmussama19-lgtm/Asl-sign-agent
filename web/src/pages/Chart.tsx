import { WordFace } from "../components/WordFace";
import { ALPHABET, WORD_SIGNS, letterImage, signVideo } from "../lib/signs";

export default function Chart() {
  return (
    <>
      <h1 className="page-title">ASL chart</h1>
      <p className="page-sub">The 26 letters of the American Sign Language alphabet, and the whole words this demo recognizes.</p>
      <div className="sign-grid">
        {ALPHABET.map((L) => (
          <div key={L} className="sign-card">
            <img src={letterImage(L)} alt={`ASL sign for ${L}`} loading="lazy" />
            <div className="row"><span className="k">{L}</span><a href={signVideo(L)} target="_blank" rel="noreferrer">Watch</a></div>
          </div>
        ))}
      </div>
      <p className="muted" style={{ marginTop: 14 }}>Drawings: public domain, from Wikimedia Commons (wpclipart.com). J and Z are movements: the drawing shows the starting pose.</p>

      <h2 className="section-title">Word signs</h2>
      <p className="section-sub">This demo recognizes 9 word signs, a lighter set that keeps it fast (the model was evaluated on 24). Watch real people sign each word, then turn on Word signs in the Sign to text settings to try it.</p>
      <div className="sign-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))" }}>
        {WORD_SIGNS.map((w) => (
          <div key={w} className="sign-card"><WordFace word={w} /></div>
        ))}
      </div>
      <p className="muted" style={{ marginTop: 14 }}>Videos open the SignASL.org dictionary, where several people sign each word. They are linked, not embedded.</p>
    </>
  );
}
