import os
import streamlit as st
from ui import inject_css, tiles_html, section, get_word_sign_gifs, word_sign_labels, _dataset_base, uses_remote_images

inject_css()

# ---------------- Hero: the whole pipeline on one real sentence ----------------
st.markdown(f'''
<div class="hero">
  <div>
    <h1>Sign in front of your webcam. The agent reads it, replies and speaks.</h1>
    <p>ASL Sign Agent recognizes the American Sign Language alphabet and a set of word signs,
    turns raw fingerspelling into a clean sentence, then holds a conversation with you,
    out loud.</p>
  </div>
  <div class="demo-card">
    <div class="demo-step">What the camera reads</div>
    {tiles_html("ILOVEU", done=5, now=5)}
    <div class="demo-step">What the agent understands</div>
    <div class="readout">I love you</div>
    <div class="demo-step">What it answers</div>
    <div class="bubble">That's very kind! How is your day going?</div>
  </div>
</div>
''', unsafe_allow_html=True)

if st.button("Open the live demo", type="primary", icon=":material/front_hand:"):
    st.switch_page("views/sign_to_text.py")

# ---------------- How it works: a real sequence ----------------
section("How it works")
st.markdown('''
<ol class="steps">
  <li><b>Camera</b>Your webcam stream is processed frame by frame.</li>
  <li><b>21 hand landmarks</b>MediaPipe locates your hand joints, so lighting and background matter less.</li>
  <li><b>Letters and word signs</b>A neural network reads each static letter, a sequence model reads moving word signs.</li>
  <li><b>Interpreting agent</b>It splits words, fixes typos and expands shorthand: "ILOVEU" becomes "I love you".</li>
  <li><b>Conversation</b>An AI model replies in your language, English or French.</li>
  <li><b>Voice</b>Your browser reads the reply out loud.</li>
</ol>
''', unsafe_allow_html=True)

n_words = len(word_sign_labels()) or 9
st.markdown(f'''
<div class="facts">
  <span><b>99.23%</b>accuracy on the 28 static signs</span>
  <span><b>86%</b>accuracy on 24 word signs</span>
  <span><b>{n_words}</b>word signs in this demo</span>
  <span><b>23,000</b>English and French words known by the agent</span>
</div>
''', unsafe_allow_html=True)

# ---------------- What you can do ----------------
section("What you can do")
c1, c2 = st.columns(2, gap="large")
with c1:
    st.page_link("views/sign_to_text.py", label="Sign to Text", icon=":material/front_hand:")
    st.caption("Fingerspell or sign whole words. After a short pause the agent interprets your "
               "sentence, answers and reads the answer out loud.")
    st.page_link("views/practice_mode.py", label="Practice", icon=":material/sports_score:")
    st.caption("Spell the word on screen, letter by letter. Adaptive drills bring back the letters "
               "you miss most.")
    st.page_link("views/text_to_sign.py", label="Text to Sign", icon=":material/keyboard:")
    st.caption("Type a sentence in English or French and watch it spelled in ASL. Export it as a GIF.")
with c2:
    st.page_link("views/chart.py", label="ASL Chart", icon=":material/sort_by_alpha:")
    st.caption("All 26 letters of the ASL alphabet, with links to videos of real signers.")
    st.page_link("views/sign_to_text.py", label="Personalization", icon=":material/tune:")
    st.caption("Teach the app your own sign in 3 gestures, or fix a letter that fails for your hand "
               "with 5 examples. No retraining needed.")
    st.page_link("views/results.py", label="Results", icon=":material/monitoring:")
    st.caption("Accuracy and per-letter scores of the letter recognition model.")

# ---------------- Setup status ----------------
section("Setup status", "What this installation can do right now. Only the first item is required.")


def check(ok, title, ok_msg, ko_msg):
    dot = '<div class="dot ok"></div>' if ok else '<div class="dot ko"></div>'
    st.markdown(f'<div class="chk">{dot}<div><div class="t">{title}</div>'
                f'<div class="d">{ok_msg if ok else ko_msg}</div></div></div>', unsafe_allow_html=True)


from conversation import is_available, model_for

c1, c2 = st.columns(2, gap="large")
with c1:
    check(os.path.exists("asl_mediapipe_mlp_model.h5") and os.path.exists("labels.json"),
          "Letter model", "Ready: alphabet recognition works.",
          "Missing: put asl_mediapipe_mlp_model.h5 and labels.json in the app folder.")
    check(os.path.exists("sign_words_model.h5"),
          "Word-sign model", f"Ready: {n_words} word signs. Turn on Word signs in the Sign to Text sidebar.",
          "Missing: run download_signs_dataset.py, then notebook 03 (see README).")
    check(_dataset_base() is not None,
          "Sign photos (optional)",
          "Found: real photos are used in the chart and Text to Sign.",
          "Not installed: public-domain drawings are used instead." if uses_remote_images()
          else "Not installed: images from assets/alphabet are used.")
    check(len(get_word_sign_gifs()) > 0,
          "Word-sign animations (optional)",
          "Ready: shown in the chart and Text to Sign.",
          "Not generated: words are fingerspelled instead. Run make_word_previews.py to add them.")
with c2:
    groq, gemini, ollama = is_available("groq"), is_available("gemini"), is_available("ollama")
    check(groq, "Groq", f"Connected: {model_for('groq')}, with {model_for('groq_fast')} as backup.",
          "Not configured: add GROQ_API_KEY to the app secrets.")
    check(gemini, "Gemini", f"Connected: {model_for('gemini')}.",
          "Not configured: add GEMINI_API_KEY to the app secrets.")
    check(ollama, "Ollama (local AI)", f"Running: {model_for('ollama')}. Nothing leaves your machine.",
          "Not running: optional, for a fully offline conversation.")
    check(True, "Local rules", "Always on: the agent can still answer simple sentences without any AI.", "")

st.caption("Fingerspelling and a closed set of word signs are a subset of ASL: this project does not "
           "translate the full grammar of the language.")
