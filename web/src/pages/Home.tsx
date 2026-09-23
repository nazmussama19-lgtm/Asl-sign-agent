import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { HandArt } from "../components/HandArt";
import { Keycaps } from "../components/Keycaps";

const DEMO = "HELLO";

export default function Home() {
  const navigate = useNavigate();
  // The hero spells HELLO on its own, one keycap at a time, once.
  const [done, setDone] = useState(0);
  useEffect(() => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) { setDone(DEMO.length); return; }
    if (done >= DEMO.length) return;
    const t = setTimeout(() => setDone((d) => d + 1), done === 0 ? 900 : 650);
    return () => clearTimeout(t);
  }, [done]);

  return (
    <>
      <section className="hero">
        <div>
          <h1>Your hands speak. The agent answers.</h1>
          <p>Sign in front of your webcam: letters light up as they are read, the agent turns them into a sentence and replies out loud. Everything runs in your browser.</p>
          <Keycaps text={DEMO} done={done} now={done < DEMO.length ? done : null} size="lg" label="HELLO spelled with keycaps" />
          <button className="btn primary" onClick={() => navigate("/sign")}>Start signing</button>
          <div className="stats">
            <div><b>99.23%</b><span>accuracy on 28 static signs</span></div>
            <div><b>86%</b><span>on 24 word signs</span></div>
            <div><b>9</b><span>word signs in this demo, to keep it light</span></div>
            <div><b>0</b><span>frames uploaded</span></div>
          </div>
        </div>
        <HandArt />
      </section>

      <h2 className="section-title">How it works</h2>
      <p className="section-sub">From your camera to a spoken reply, in six steps.</p>
      <ol className="steps">
        <li><b>Camera</b>Your webcam stream stays on your computer.</li>
        <li><b>21 hand landmarks</b>MediaPipe locates your hand joints, so lighting and background matter less.</li>
        <li><b>Letters and word signs</b>A neural network reads each letter; a sequence model reads moving word signs.</li>
        <li><b>Interpreting agent</b>It splits words, fixes typos and expands shorthand: "ILOVEU" becomes "I love you".</li>
        <li><b>Conversation</b>An AI model replies in your language, English or French.</li>
        <li><b>Voice</b>Your browser reads the reply out loud.</li>
      </ol>

      <h2 className="section-title">What you can do</h2>
      <p className="section-sub">Six pages, the same models behind each.</p>
      <div className="links">
        <Link className="link-card" to="/sign"><b>Sign to text</b><span>Fingerspell or sign whole words; the agent interprets, answers and speaks.</span></Link>
        <Link className="link-card" to="/practice"><b>Practice</b><span>Spell the word on screen. Adaptive drills bring back the letters you miss most.</span></Link>
        <Link className="link-card" to="/text"><b>Text to sign</b><span>Type a sentence in English or French and watch it spelled, then export a GIF.</span></Link>
        <Link className="link-card" to="/chart"><b>ASL chart</b><span>The 26 letters and the 9 word signs of this demo, with videos of real signers.</span></Link>
        <Link className="link-card" to="/sign"><b>Personalization</b><span>Teach your own sign in 3 gestures, or fix a letter with 5 examples of your hand.</span></Link>
        <Link className="link-card" to="/results"><b>Results</b><span>How accurate the models are, sign by sign.</span></Link>
      </div>

      <p className="muted" style={{ marginTop: 48 }}>
        Fingerspelling and a closed set of word signs are a subset of ASL: this project does not translate the full grammar of the language.{" "}
        <a href="https://github.com/nazmussama19-lgtm/Asl-sign-agent">Source code on GitHub</a>.
      </p>
    </>
  );
}
